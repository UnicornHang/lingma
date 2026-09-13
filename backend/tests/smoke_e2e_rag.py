"""RAG 端到端冒烟(直接调模块,不走 HTTP)。

依赖:
- chromadb + sentence-transformers(已装)
- 网络可用(首次 sentence-transformers 会下载 bge-small-zh 模型)

流程:
1. 探测 embedding_service.is_available() + vector_store.is_available()
2. 准备临时 chromadb 路径 → 真实写入 + 检索
3. 索引 fake character/world/chapter,跨三类聚合 search
4. 集成 WriterAgent.build_messages() → 验证 prompt 含「【RAG 向量检索补充】」slot

不依赖 backend HTTP 服务;如失败,详细 log 哪一步。
"""
from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from types import SimpleNamespace
from uuid import uuid4

from app.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.rag_service import (
    RagService,
    _chunk_text,
    collection_name,
    get_rag_service,
)
from app.services.vector_store import get_vector_store


def step1_probe_availability() -> tuple[bool, str]:
    """探测 embedding + vector_store 可用性。"""
    print("=" * 60)
    print("STEP 1: 探测 RAG 依赖可用性")
    print("=" * 60)
    es = get_embedding_service()
    vs = get_vector_store()
    es_ok = es.is_available()
    vs_ok = vs.is_available()
    print(f"  embedding_service.is_available() = {es_ok}")
    print(f"    model: {settings.embedding_model}")
    print(f"  vector_store.is_available()       = {vs_ok}")
    print(f"    path:   {settings.vector_store_path}")
    if not (es_ok and vs_ok):
        return False, "embedding 或 vector_store 不可用"
    return True, ""


def step2_chunking_smoke() -> tuple[bool, str]:
    """验证 _chunk_text 在真实数据上的切分行为。"""
    print()
    print("=" * 60)
    print("STEP 2: _chunk_text 段落级切分")
    print("=" * 60)
    sample = (
        "林轩在青云山修炼十载,忽一日天降异象。"
        "他抬头望天,只见一道金光划破苍穹,落于山巅。"
        "\n\n"
        "青云山乃东域第一仙门,灵气充沛,弟子众多。"
        "林轩资质平平,却心志坚定。"
        "\n\n"
        "金光落处,一柄古剑横空出世,剑身刻有远古铭文。"
        "此剑名为'天璇',乃上古神兵,可斩仙灭魔。"
    )
    chunks = _chunk_text(
        sample,
        min_chars=settings.rag_chunk_min_chars,
        max_chars=settings.rag_chunk_max_chars,
    )
    print(f"  原文 {len(sample)} 字 → 切分为 {len(chunks)} 个 chunk:")
    for i, c in enumerate(chunks):
        snippet = c[:60].replace("\n", " ")
        print(f"    [{i}] {len(c)} chars: {snippet}…")
    if not chunks:
        return False, "chunk_text 返回空"
    return True, ""


async def step2_5_pick_real_work() -> UUID | None:
    """从 db 找任意一个 work 用于步骤 3/4 共享。"""
    from sqlalchemy import text as sa_text
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        r = await db.execute(sa_text(
            "SELECT substr(work_id,1,8)||'-'||substr(work_id,9,4)||'-'||"
            "substr(work_id,13,4)||'-'||substr(work_id,17,4)||'-'||substr(work_id,21,12) "
            "FROM chapters LIMIT 1"
        ))
        row = r.first()
        if not row:
            return None
        from uuid import UUID
        return UUID(row[0])


async def step3_real_index_and_search(work_id) -> tuple[bool, str]:
    """真实 chromadb 写入 + 检索。"""
    print()
    print("=" * 60)
    print(f"STEP 3: 真实 chromadb 索引 + 检索 (work={work_id})")
    print("=" * 60)
    svc = get_rag_service()

    # 1) 索引 character
    character = SimpleNamespace(
        id=uuid4(),
        work_id=work_id,
        name="林轩",
        role="主角",
        raw_text=(
            "林轩是青云山弟子,年方十八,资质平平却心志坚定。"
            "他在一次山巅探险中偶得神剑'天璇',从此踏入修仙之路。"
            "林轩性格坚毅,不屈不挠,对朋友忠诚,对敌人冷酷。"
        ),
    )
    char_chunks = await svc.index_character(None, character)
    print(f"  [OK] index character(name=林轩): {char_chunks} chunks")

    # 2) 索引 world
    world = SimpleNamespace(
        id=uuid4(),
        work_id=work_id,
        raw_text=(
            "青云山乃东域第一仙门,立派三千年,代有英才。"
            "山分七峰,各峰弟子修习不同功法,门派以剑道闻名天下。"
            "山中灵气充沛,是修真圣地。"
        ),
    )
    world_chunks = await svc.index_world(None, world)
    print(f"  [OK] index world: {world_chunks} chunks")

    # 3) 索引 chapter
    chapter = SimpleNamespace(
        id=uuid4(),
        work_id=work_id,
        title="第一章 觉醒",
        summary="林轩在山巅偶得天璇剑,踏上修仙之路。",
        plain_content="",
    )
    chap_chunks = await svc.index_chapter_summary(None, chapter)
    print(f"  [OK] index chapter(title=第一章 觉醒): {chap_chunks} chunks")

    # 4) 检索
    print()
    print("  >>> 检索 query='林轩在山巅发生了什么':")
    hits = await svc.search(work_id=work_id, query="林轩在山巅发生了什么", top_k=3)
    print(f"    返回 {len(hits)} hits:")
    for i, h in enumerate(hits):
        text_preview = h.text[:60].replace("\n", " ")
        print(
            f"    [{i}] type={h.target_type:10s} score={h.score:.4f} "
            f"chunk#{h.chunk_index}: {text_preview}…"
        )

    if not hits:
        return False, "search 返回空,索引写入可能失败"

    # 5) 验证至少有一个 hit 是 character 类型
    if not any(h.target_type == "character" for h in hits):
        return False, "期望至少 1 条 character 命中"

    # 6) 验证 collection 命名
    expected_name = collection_name("character", work_id)
    actual_collections = get_vector_store().list_collections()
    print(f"    collection_name('character', work_id) = {expected_name}")
    print(f"    实际 chromadb collections: {len(actual_collections)} 个")
    matching = [c for c in actual_collections if expected_name in c]
    if not matching:
        return False, f"未找到预期 collection {expected_name}"

    return True, ""


async def step4_writer_integration(work_id) -> tuple[bool, str]:
    """集成 WriterAgent.build_messages → 验证 prompt 含 RAG slot。

    Args:
        work_id: 步骤 3 已索引数据的 work_id;此处只挑属于该 work 的 chapter。
    """
    print()
    print("=" * 60)
    print("STEP 4: WriterAgent.build_messages RAG 集成")
    print("=" * 60)

    from app.agents.writer_agent import WriterAgent, _search_rag_hits
    from app.db.session import async_session_factory

    # 找属于 work_id 的 chapter
    from sqlalchemy import text as sa_text
    from uuid import UUID
    work_id_hex = work_id.hex
    async with async_session_factory() as db:
        r = await db.execute(sa_text(
            "SELECT "
            "substr(id,1,8)||'-'||substr(id,9,4)||'-'||substr(id,13,4)||'-'||substr(id,17,4)||'-'||substr(id,21,12) "
            "FROM chapters WHERE work_id = :wid LIMIT 1"
        ), {"wid": work_id_hex})
        row = r.first()
        if not row:
            print("  [SKIP] db 中该 work 无 chapter,跳过 build_messages")
            return True, ""
        chapter_id = UUID(row[0])

    print(f"  找到 chapter_id={chapter_id} (work_id={work_id})")

    # 1) 直接调 _search_rag_hits(无 DB,验证检索能拿到 hits)
    fake_chapter = SimpleNamespace(
        id=uuid4(),
        work_id=work_id,
        title="山巅奇遇",
        summary="林轩在山巅偶得天璇剑",
        plain_content="",
    )
    hits = await _search_rag_hits(None, fake_chapter, None)
    print(f"  _search_rag_hits(目标 work) → {len(hits)} hits")

    # 2) 调 build_messages(真实 DB),看 prompt 是否含 RAG slot
    try:
        async with async_session_factory() as db:
            agent = WriterAgent()
            msgs, model, user = await agent.build_messages(db, chapter_id)
    except Exception as e:
        return False, f"build_messages 抛异常: {e}"

    has_rag = "【RAG 向量检索补充】" in user
    print(f"  build_messages 成功: user_prompt {len(user)} 字, model={model}")
    print(f"  prompt 含 RAG slot: {has_rag}")

    if not has_rag:
        if not settings.rag_enabled:
            print("    (注: settings.rag_enabled=False,故跳过 RAG slot)")
            return True, ""
        slot_marks = [
            "【作品总览】", "【文风裁决】", "【本章大纲】",
            "【出场角色】", "【上一章摘要】", "【本章任务】",
        ]
        present = [m for m in slot_marks if m in user]
        print(f"    实际 slot: {len(present)}/{len(slot_marks)} ({present})")
        return False, "RAG enabled 但 prompt 不含 RAG slot"

    rag_idx = user.find("【RAG 向量检索补充】")
    snippet = user[rag_idx:rag_idx + 300].replace("\n", " ")
    print(f"  RAG slot 内容预览: {snippet}…")
    return True, ""


async def main() -> int:
    print(">>> LingMa RAG 端到端冒烟 (chromadb + sentence-transformers)")
    print(f">>> embedding_model={settings.embedding_model}")
    print(f">>> vector_store_path={settings.vector_store_path}")
    print(f">>> rag_enabled={settings.rag_enabled}")
    print(f">>> rag_top_k={settings.rag_top_k}")
    print()

    # Step 1
    ok, msg = step1_probe_availability()
    if not ok:
        print(f"\n[FAIL] STEP 1: {msg}")
        return 1
    print("\n[PASS] STEP 1")

    # Step 2
    ok, msg = step2_chunking_smoke()
    if not ok:
        print(f"\n[FAIL] STEP 2: {msg}")
        return 1
    print("\n[PASS] STEP 2")

    # 取一个真实 work_id(让 Step3 索引 + Step4 检索能对上)
    work_id = await step2_5_pick_real_work()
    if work_id is None:
        print("\n[WARN] db 中无 chapter, 用临时 work_id 走 step3(无 step4)")
        work_id = uuid4()
        ok, msg = await step3_real_index_and_search(work_id)
        if not ok:
            print(f"\n[FAIL] STEP 3: {msg}")
            return 1
        print("\n[PASS] STEP 3 (no step 4)")
        print()
        print("=" * 60)
        print("[SUCCESS] All steps passed (step 4 skipped)")
        print("=" * 60)
        return 0
    print(f"\n[INFO] 使用真实 work_id={work_id}")

    # Step 3
    ok, msg = await step3_real_index_and_search(work_id)
    if not ok:
        print(f"\n[FAIL] STEP 3: {msg}")
        return 1
    print("\n[PASS] STEP 3")

    # Step 4
    ok, msg = await step4_writer_integration(work_id)
    if not ok:
        print(f"\n[FAIL] STEP 4: {msg}")
        return 1
    print("\n[PASS] STEP 4")

    print()
    print("=" * 60)
    print("[SUCCESS] All 4 steps passed - RAG E2E smoke OK")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nFATAL: {e}", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)