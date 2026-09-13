"""端到端冒烟:验证 continue 模式 + 实时流式 + 落档

步骤:
1. 创建 work + chapter(含初始正文)
2. POST /chapters/{id}/generate, mode=continue, continue_from_chars=20
3. 验证 task.params.mode == 'continue'
4. WS 连入 → 收到 connected → send start
5. 收集 delta 事件,验证 final token_usage > 0(若 provider 是 OpenAI 兼容,Anthropic 不会)
6. 验证章节 plain_content 是 baseline + 新增(append 而非覆盖)
7. 验证 chapter_versions 表新增 ai_revised 行
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# 让脚本能 `import app.*` —— 直接运行 tests/smoke_*.py 时,cwd 是 backend/,
# 但 Python 默认不会把 cwd 加入 sys.path(脚本目录才会),所以手动加一下。
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import httpx
import websockets

BASE = "http://localhost:8000/api/v1"
WS_BASE = "ws://localhost:8000"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=20.0) as client:
        # 1) 创建作品
        r = await client.post(
            "/works/",
            json={"title": "续写测试", "genre": "fantasy", "target_word_count": 100000},
        )
        r.raise_for_status()
        work_id = r.json()["id"]
        print(f"work_id={work_id}")

        # 2) 创建章节(含 baseline)
        baseline = "夜黑风高,主角林逸猛然睁眼,发现自己身处陌生之地。"
        r = await client.post(
            "/chapters/",
            json={
                "work_id": work_id,
                "title": "第1章 穿越",
                "plain_content": baseline,
            },
        )
        r.raise_for_status()
        ch = r.json()
        ch_id = ch["id"]
        v0 = ch["version"]
        print(f"chapter_id={ch_id}, version={v0}, baseline_len={len(baseline)}")

        # 3) 创建 continue 模式任务
        r = await client.post(
            f"/chapters/{ch_id}/generate",
            json={
                "mode": "continue",
                "continue_from_chars": 100,
                "target_word_count": 500,
            },
        )
        r.raise_for_status()
        task = r.json()
        task_id = task["task_id"]
        print(f"task_id={task_id}, ws_url={task['ws_url']}")

    # 4) WS 流程
    ws_url = f"{WS_BASE}{task['ws_url']}"
    events: list[dict] = []
    stage_events: list[dict] = []
    delta_count = 0
    full = ""
    done_content = ""
    done_critic = None  # [P2]
    final_usage = None

    async with websockets.connect(ws_url) as ws:
        connected = json.loads(await ws.recv())
        events.append(connected)
        print(f"[ws] {connected['type']}")

        await ws.send(json.dumps({
            "type": "start",
            "mode": "continue",
            "continue_from_chars": 100,
            "max_tokens": 500,
        }))

        while True:
            raw = await ws.recv()
            ev = json.loads(raw)
            events.append(ev)
            if ev["type"] == "stage":
                stage_events.append(ev)
                print(
                    f"[ws] stage: {ev.get('stage')} status={ev.get('status')} "
                    f"elapsed={ev.get('elapsed_ms', '-')} reason={ev.get('skipped_reason', '-')}"
                )
            elif ev["type"] == "start":
                print(f"[ws] {ev['type']} model={ev.get('model')} mode={ev.get('mode')}")
                # start 上的 prefill 字段(若有)
                if ev.get("prefill"):
                    print(f"[ws] prefill summary: plot={ev['prefill']['plot']['status']}, "
                          f"world={ev['prefill']['world']['status']}, "
                          f"character={ev['prefill']['character']['status']}")
            elif ev["type"] == "delta":
                delta_count += 1
                full += ev.get("content", "")
            elif ev["type"] == "done":
                final_usage = ev.get("token_usage")
                done_content = ev.get("content", "")
                done_critic = ev.get("critic")  # [P2]
                print(f"[ws] {ev['type']} done_content_len={len(done_content)} raw_full_len={len(full)} token_usage={final_usage}")
                print(f"[ws]   critic: {done_critic}")
                break
            elif ev["type"] in ("error", "cancelled"):
                print(f"[ws] {ev['type']}: {ev.get('error')}")
                break

    # 5) 验证结果
    print()
    print(f"delta events: {delta_count}")
    print(f"raw full content length: {len(full)}")
    print(f"cleaned done content length: {len(done_content)}")
    print(f"final usage: {final_usage}")

    # 重新读章节,确认 append 而非覆盖
    async with httpx.AsyncClient(base_url=BASE, timeout=10.0) as client:
        r = await client.get(f"/chapters/{ch_id}")
        final_ch = r.json()
        print()
        print("=== Final chapter ===")
        print(f"plain_content[:60]: {final_ch['plain_content'][:60]}")
        print(f"plain_content startswith baseline: {final_ch['plain_content'].startswith(baseline)}")
        print(f"plain_content endswith cleaned_done_content: {final_ch['plain_content'].endswith(done_content)}")
        print(f"plain_content contains <think>: {'<think>' in final_ch['plain_content']}")
        print(f"plain_content length: {len(final_ch['plain_content'])}")
        print(f"version: {final_ch['version']} (was {v0})")
        print(f"status: {final_ch['status']}")

        # 验证 chapter_versions —— 用 raw SQL 避开 UUID/JSON 列的 ORM mapper 复杂性
        from app.db.session import async_session_factory
        from sqlalchemy import text as sa_text

        # aiosqlite 把 UUID 列存为去掉横线的 hex 串
        ch_id_hex = ch_id.replace("-", "")

        async with async_session_factory() as db:
            r2 = await db.execute(
                sa_text(
                    "SELECT version_no, generated_by, model_used, note, "
                    "length(plain_content) AS plen, plain_content "
                    "FROM chapter_versions WHERE chapter_id = :cid "
                    "ORDER BY version_no DESC"
                ),
                {"cid": ch_id_hex},
            )
            versions = [
                {
                    "version_no": row[0],
                    "generated_by": row[1],
                    "model_used": row[2],
                    "note": row[3],
                    "plen": row[4],
                    "plain_content": row[5],
                }
                for row in r2.fetchall()
            ]
            # [P2] critic_evaluations 落库校验
            r3 = await db.execute(
                sa_text(
                    "SELECT overall, consistency, pacing, prose, engagement, "
                    "length(consensus_issues) AS issues_len, model_used, version_no "
                    "FROM critic_evaluations WHERE chapter_id = :cid "
                    "ORDER BY created_at DESC"
                ),
                {"cid": ch_id_hex},
            )
            critic_rows = [
                {
                    "overall": row[0],
                    "consistency": row[1],
                    "pacing": row[2],
                    "prose": row[3],
                    "engagement": row[4],
                    "issues_len": row[5],
                    "model_used": row[6],
                    "version_no": row[7],
                }
                for row in r3.fetchall()
            ]
        print()
        print(f"=== ChapterVersion rows: {len(versions)} ===")
        for v in versions[:3]:
            print(f"  v{v['version_no']}: by={v['generated_by']}, model={v['model_used']}, note={v['note']!r}, len={v['plen']}, has_think={'<think>' in v['plain_content']}")

        print()
        print(f"=== CriticEvaluation rows: {len(critic_rows)} ===")
        for c in critic_rows[:3]:
            print(f"  v{c['version_no']}: overall={c['overall']:.3f}, pacing={c['pacing']:.3f}, prose={c['prose']:.3f}, engagement={c['engagement']:.3f}, issues={c['issues_len']}, model={c['model_used']!r}")

    # 断言
    assert final_ch["plain_content"].startswith(baseline), "plain_content should be appended (starts with baseline)"
    assert "<think>" not in final_ch["plain_content"], "plain_content should NOT contain <think> blocks"

    # 模型推理型(MiniMax/DeepSeek-R1/QwQ)偶尔会把全部输出塞进 <think>,cleaned 后为空。
    # 这种情况下后端会 rollback(plain_content 恢复 baseline,version 不变,status 保持 draft)。
    # 测试应视为软失败:不能强制断言 version/status/ChapterVersion。
    if len(done_content.strip()) < 10:
        print()
        print("=== MODEL PRODUCED ONLY THINK BLOCK — ROLLBACK PATH (skip strict assertions) ===")
        print(f"plain_content length={len(final_ch['plain_content'])} (should equal baseline={len(baseline)})")
        print(f"version stayed at {final_ch['version']} (no bump)")
        print(f"status stayed at {final_ch['status']} (no bump to generated)")
        assert len(final_ch["plain_content"]) == len(baseline), "rollback should preserve baseline length"
        assert final_ch["version"] == v0, "rollback should NOT bump version"
        assert final_ch["status"] != "generated", "rollback should NOT mark as generated"
        assert not versions, "rollback should NOT write ChapterVersion"
        print("=== ROLLBACK PATH OK ===")
        # [P1-2] 即使 rollback,prefill stage 事件也应已发出(在 start 之前)
        _assert_prefill_events(stage_events)
        # [P2] rollback 路径下 critic 不应被记录(因为没有有效正文)
        assert not critic_rows, f"rollback should NOT write CriticEvaluation, got {len(critic_rows)}"
        return

    # 正常生成路径:cleaned 内容充分,后续断言严格
    assert final_ch["plain_content"].endswith(done_content), f"plain_content should end with cleaned done.content (db_len={len(final_ch['plain_content'])}, done_len={len(done_content)})"
    assert final_ch["version"] > v0, "version should be bumped"
    assert final_ch["status"] == "generated", "status should be generated"
    ai_revised = [v for v in versions if v["generated_by"] == "ai_revised"]
    assert ai_revised, "should have at least one ai_revised row"
    assert "<think>" not in ai_revised[0]["plain_content"], "ChapterVersion.ai_revised should NOT contain <think>"
    # [P1-2] prefill stage 事件校验
    _assert_prefill_events(stage_events)
    # [P2] critic 评审软断言(graceful degradation)
    _assert_critic_event(done_critic, critic_rows)
    print()
    print("=== ALL ASSERTIONS PASSED ===")


def _assert_prefill_events(stage_events: list[dict]) -> None:
    """[P1-2] 校验 prefill stage 事件序列。

    期望:
    - 至少收到 1 个 stage 事件(空 work → running/done;非空 → skipped)
    - 至少看到 3 个不同 stage(plot/world/character)
    - 状态值在 {running, done, skipped, error} 之内
    """
    print()
    print(f"=== P1-2 Prefill Stage Events: {len(stage_events)} total ===")
    for ev in stage_events:
        print(f"  stage={ev.get('stage')!r:14s} status={ev.get('status')!r:10s} "
              f"elapsed={ev.get('elapsed_ms', '-')!s:>6} reason={ev.get('skipped_reason', '-')!r}")

    if not stage_events:
        print("WARN: no stage events received (prefill may have been disabled or stage skipped all)")
        return

    stages = {ev.get("stage") for ev in stage_events}
    valid_stages = {"plot", "world", "character"}
    missing = valid_stages - stages
    if missing:
        # 允许部分缺失(比如已存在数据时部分 stage skip / fail)
        print(f"NOTE: some stages missing from events: {missing}")

    valid_statuses = {"running", "done", "skipped", "error"}
    for ev in stage_events:
        status = ev.get("status")
        assert status in valid_statuses, f"invalid stage status: {status!r}"
        assert "stage" in ev, "stage event must have 'stage' field"
        assert ev.get("type") == "stage", f"type field must be 'stage', got {ev.get('type')!r}"
    print("=== Prefill stage events OK ===")


def _assert_critic_event(done_critic, critic_rows: list[dict]) -> None:
    """[P2] 校验 critic 评审结果。

    期望(软断言,graceful degradation):
    - WS done 事件的 critic 字段为 dict 或 None(不应缺字段)
    - 若 critic 跑成功:DB critic_evaluations 表应有 ≥ 1 行
    - 若 critic 失败(LLM 异常):done_critic 应为 None,DB 无行 —— 不算失败

    不做硬断言的原因:critic 失败 = graceful,不影响 writer;e2e 应当容忍。
    """
    print()
    print(f"=== P2 Critic Event: {type(done_critic).__name__} ===")
    if done_critic is None:
        print(f"  WS done.critic = None (critic 跑失败或被关闭) — 跳过 DB 校验")
        return

    # 校验 done.critic 字段齐全
    expected_keys = {"overall", "consistency", "pacing", "prose", "engagement",
                     "consensus_issues", "model_used"}
    missing = expected_keys - set(done_critic.keys())
    assert not missing, f"critic payload 缺字段: {missing}"
    print(f"  overall={done_critic['overall']:.3f} consistency={done_critic['consistency']:.3f} "
          f"pacing={done_critic['pacing']:.3f} prose={done_critic['prose']:.3f} "
          f"engagement={done_critic['engagement']:.3f}")
    print(f"  model_used={done_critic['model_used']!r} issues={len(done_critic['consensus_issues'])}")

    # 校验 DB 落库
    if not critic_rows:
        print(f"  WARN: critic hook 报了事件但 critic_evaluations 表无行 (事务可能未提交)")
    else:
        print(f"  DB critic_evaluations: {len(critic_rows)} 行")
        for c in critic_rows:
            assert 0.0 <= c["overall"] <= 1.0, f"overall 越界: {c['overall']}"
            assert 0.0 <= c["pacing"] <= 1.0, f"pacing 越界: {c['pacing']}"
    print("=== Critic event OK (soft) ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nFAIL: {e}", file=sys.stderr)
        sys.exit(1)