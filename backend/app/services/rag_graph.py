"""RAG 问答编排（支持多轮对话；未命中知识库时婉拒，不用自身知识补答）。"""
from collections.abc import Iterator
from typing import TypedDict

from app.services.rag import (
    NO_CONTEXT_ANSWER,
    answer_with_qwen,
    build_prompt,
    build_search_query,
    retrieve_context,
)


class RAGState(TypedDict, total=False):
    tenant_id: int
    kb_ids: list[int]
    question: str
    history: list[dict]
    context: str
    sources: list[dict]
    messages: list[dict]


def run_rag_stream(
    tenant_id: int,
    kb_ids: list[int],
    question: str,
    history: list[dict] | None = None,
) -> tuple[Iterator[str], list[dict]]:
    history = history or []
    search_q = build_search_query(question, history)
    filter_q = f"{question} {search_q}".strip()
    context, sources = retrieve_context(
        tenant_id,
        kb_ids,
        search_q,
        filter_question=filter_q,
        rank_question=question,
    )
    if not sources and search_q != question:
        context, sources = retrieve_context(
            tenant_id,
            kb_ids,
            question,
            filter_question=filter_q,
            rank_question=question,
        )

    from_kb = bool(sources) and bool((context or "").strip())
    # 未命中：直接婉拒，不调大模型，避免用自身知识展开
    if not from_kb:
        answer = NO_CONTEXT_ANSWER
        out_sources: list[dict] = []
    else:
        messages = build_prompt(question, context, history, from_kb=True)
        answer = answer_with_qwen(
            messages,
            question=question,
            sources=sources,
            allow_empty_sources=False,
        )
        out_sources = sources
        ans = (answer or "").strip()
        soft_miss_markers = (
            "知识库里翻了",
            "没找到这块",
            "好像还没入库",
            "没有相关",
            "没有靠谱资料",
            "只能依据已上传",
            NO_CONTEXT_ANSWER[:12],
        )
        if ans == NO_CONTEXT_ANSWER or any(m in ans for m in soft_miss_markers):
            out_sources = []

    def chunk_stream():
        step = 48
        for i in range(0, len(answer), step):
            yield answer[i : i + step]

    return chunk_stream(), out_sources
