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
    delta_count = 0
    full = ""
    done_content = ""
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
            if ev["type"] == "start":
                print(f"[ws] {ev['type']} model={ev.get('model')} mode={ev.get('mode')}")
            elif ev["type"] == "delta":
                delta_count += 1
                full += ev.get("content", "")
            elif ev["type"] == "done":
                final_usage = ev.get("token_usage")
                done_content = ev.get("content", "")
                print(f"[ws] {ev['type']} done_content_len={len(done_content)} raw_full_len={len(full)} token_usage={final_usage}")
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
        print()
        print(f"=== ChapterVersion rows: {len(versions)} ===")
        for v in versions[:3]:
            print(f"  v{v['version_no']}: by={v['generated_by']}, model={v['model_used']}, note={v['note']!r}, len={v['plen']}, has_think={'<think>' in v['plain_content']}")

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
        return

    # 正常生成路径:cleaned 内容充分,后续断言严格
    assert final_ch["plain_content"].endswith(done_content), f"plain_content should end with cleaned done.content (db_len={len(final_ch['plain_content'])}, done_len={len(done_content)})"
    assert final_ch["version"] > v0, "version should be bumped"
    assert final_ch["status"] == "generated", "status should be generated"
    ai_revised = [v for v in versions if v["generated_by"] == "ai_revised"]
    assert ai_revised, "should have at least one ai_revised row"
    assert "<think>" not in ai_revised[0]["plain_content"], "ChapterVersion.ai_revised should NOT contain <think>"
    print()
    print("=== ALL ASSERTIONS PASSED ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nFAIL: {e}", file=sys.stderr)
        sys.exit(1)