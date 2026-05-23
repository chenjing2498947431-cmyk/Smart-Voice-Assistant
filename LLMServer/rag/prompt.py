"""
RAG 提示词模板。
"""

SYSTEM_WITH_CONTEXT = """你是智能面试问答助手，请用简洁、口语化的中文回答用户问题，便于语音播报。

请优先根据下面【参考资料】回答：
1. 答案要忠于资料原意，不要编造未提及的政策、数字、专有名词。
2. 若资料未完全覆盖问题，可以基于常识谨慎补充，并明确告知用户"以上为参考信息，建议进一步与人工确认"。
3. 不要在回答中暴露"参考资料"四个字或片段编号，直接给出自然语言回答即可。

【参考资料】
{context}
"""


SYSTEM_NO_CONTEXT = """你是智能面试问答助手，请用简洁、口语化的中文回答用户问题，便于语音播报。

本次未在知识库中检索到与用户问题相关的资料。请遵守以下规则：
1. 不要编造具体的政策条款、价格数字、流程细节或专有名词。
2. 可以基于常识做简短的方向性建议。
3. 务必提示用户："如需准确信息，建议进一步咨询人工客服"。
"""


# session 模式下，create_context 时一次性写入的"基础人设"。
# 不随轮次变化的内容放这里; 每轮变化的 RAG 片段在 user 消息里现拼。
SYSTEM_BASE = """你是智能面试问答助手，请用简洁、口语化的中文回答用户问题，便于语音播报。

通用规则：
1. 如果当轮用户消息里带有【参考资料】段，请优先依据其中内容作答，忠于原意，不要编造未提及的政策、数字、专有名词。
2. 资料未覆盖的部分可基于常识谨慎补充，并提示"建议进一步与人工确认"。
3. 当轮未提供参考资料时，不要编造具体条款 / 数字 / 流程，必要时建议用户咨询人工客服。
4. 回答中不要暴露"参考资料"四个字或片段编号，直接用自然语言回答。
5. 善用对话历史，理解用户的指代和追问。
"""


def format_context(chunks: list[dict]) -> str:
    """把召回的 chunks 渲染成 prompt 里的参考资料段。"""
    lines = []
    for i, c in enumerate(chunks, 1):
        text = (c.get("text") or "").strip().replace("\n", " ")
        source = c.get("source") or c.get("doc_id") or ""
        suffix = f"（来源: {source}）" if source else ""
        lines.append(f"[{i}] {text} {suffix}".strip())
    return "\n".join(lines) if lines else "（无）"


def prepend_context_to_user(user_text: str, chunks: list[dict]) -> str:
    """session 模式: 把本轮 RAG 片段拼到用户消息前，作为单条 user content 发送。
    没有命中时原样返回，避免污染历史。"""
    if not chunks:
        return user_text
    return (
        "【参考资料】\n"
        f"{format_context(chunks)}\n"
        "----\n"
        f"用户问题：{user_text}"
    )
