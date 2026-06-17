import json
import os
import re
from functools import lru_cache

from langchain_core.tools import tool

from rag.rag_service import RagSummarizeService
from utils.path_tool import get_abs_path

rag = RagSummarizeService()

CYBERPUNK_CHUNKS_PATH = "data/cyberpunk_edgerunners_rag_kb_pack(1)/cyberpunk_edgerunners_rag_chunks.jsonl"
SPOILER_ORDER = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "Full": 4}


@lru_cache(maxsize=1)
def _load_cyberpunk_chunks() -> tuple[dict, ...]:
    """Load structured Cyberpunk: Edgerunners chunks for deterministic tools."""
    chunks_path = get_abs_path(CYBERPUNK_CHUNKS_PATH)
    if not os.path.exists(chunks_path):
        return tuple()

    chunks = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            item.setdefault("spoiler_level", "S1")
            item.setdefault("tags", [])
            chunks.append(item)
    return tuple(chunks)


def _spoiler_allowed(item_level: str, max_level: str) -> bool:
    item_score = SPOILER_ORDER.get(item_level, SPOILER_ORDER["S1"])
    max_score = SPOILER_ORDER.get(max_level, SPOILER_ORDER["S1"])
    return item_score <= max_score


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _query_terms(text: str) -> list[str]:
    raw = re.split(r"[\s,，。！？!?、/|:：；;（）()《》“”\"'`]+", text or "")
    terms = [term.lower() for term in raw if len(term.strip()) >= 2]
    compact = _normalize_query(text)
    if re.search(r"[\u4e00-\u9fff]", compact):
        for size in (2, 3, 4):
            terms.extend(compact[index:index + size] for index in range(0, max(len(compact) - size + 1, 0)))
    seen = set()
    unique_terms = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        unique_terms.append(term)
    return unique_terms


def _chunk_text(item: dict) -> str:
    tags = " ".join(item.get("tags") or [])
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "doc_type", "content", "retrieval_text")
    ) + " " + tags


def _score_chunk(query: str, item: dict) -> int:
    normalized_query = _normalize_query(query)
    text = _chunk_text(item).lower()
    normalized_text = _normalize_query(text)
    score = 0

    if normalized_query and normalized_query in normalized_text:
        score += 20

    title = str(item.get("title") or "").lower()
    if title and _normalize_query(title) in normalized_query:
        score += 16

    for tag in item.get("tags") or []:
        normalized_tag = _normalize_query(str(tag))
        if normalized_tag and normalized_tag in normalized_query:
            score += 8

    for term in _query_terms(query):
        if term in text:
            score += 3
        if term in title:
            score += 5

    return score


def _format_chunk(item: dict, index: int | None = None) -> str:
    prefix = f"{index}. " if index is not None else ""
    tags = "、".join(item.get("tags") or [])
    tag_text = f"；标签：{tags}" if tags else ""
    return (
        f"{prefix}{item.get('title', '未命名条目')} "
        f"[{item.get('doc_type', '资料')} / {item.get('spoiler_level', 'S1')}]{tag_text}\n"
        f"{item.get('content', '').strip()}"
    )


@tool(description="从本地知识库中检索并总结《赛博朋克：边缘行者》相关资料，适合剧情、设定、角色、音乐、联动、推荐等问题。")
def rag_summarize(query: str):
    """知识库问答工具，直接代理到 RAG 服务。"""
    return rag.rag_summarize(query)


@tool(description="按剧透等级检索《赛博朋克：边缘行者》结构化知识库。spoiler_level 可选 S0、S1、S2、S3、Full。")
def search_cyberpunk_kb(query: str, spoiler_level: str = "S1", max_results: int = 5):
    """Return structured Cyberpunk KB snippets with spoiler filtering."""
    chunks = _load_cyberpunk_chunks()
    if not chunks:
        return "未找到《赛博朋克：边缘行者》结构化知识库。"

    spoiler_level = spoiler_level if spoiler_level in SPOILER_ORDER else "S1"
    max_results = max(1, min(int(max_results), 8))

    scored = []
    for item in chunks:
        if not _spoiler_allowed(item.get("spoiler_level", "S1"), spoiler_level):
            continue
        score = _score_chunk(query, item)
        if score > 0:
            scored.append((score, item))

    if not scored:
        return f"在 {spoiler_level} 剧透等级内未检索到足够资料。"

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [item for _, item in scored[:max_results]]
    return "\n\n".join(_format_chunk(item, index + 1) for index, item in enumerate(selected))


@tool(description="查询《赛博朋克：边缘行者》指定集数摘要。episode 为 1-10，spoiler_level 可选 S0、S1、S2、S3、Full。")
def get_episode_summary(episode: int, spoiler_level: str = "S1"):
    """Return a structured episode summary when the spoiler level permits it."""
    try:
        episode_number = int(episode)
    except (TypeError, ValueError):
        return "集数必须是 1 到 10 的数字。"
    if episode_number < 1 or episode_number > 10:
        return "《赛博朋克：边缘行者》第一季共 10 集，请输入 1 到 10。"

    spoiler_level = spoiler_level if spoiler_level in SPOILER_ORDER else "S1"
    episode_marker = f"第{episode_number:02d}集"
    for item in _load_cyberpunk_chunks():
        title = str(item.get("title") or "")
        if episode_marker not in title:
            continue
        item_level = item.get("spoiler_level", "S1")
        if not _spoiler_allowed(item_level, spoiler_level):
            return (
                f"第 {episode_number} 集资料属于 {item_level} 剧透等级，"
                f"当前允许等级为 {spoiler_level}。如果你允许剧透，请提高 spoiler_level。"
            )
        return _format_chunk(item)

    return f"未找到第 {episode_number} 集的结构化摘要。"


@tool(description="查询《赛博朋克：边缘行者》角色资料。name 可填大卫、露西、丽贝卡、曼恩、琦薇、法拉第、亚当重锤等。")
def get_character_profile(name: str, spoiler_level: str = "S1"):
    """Return character-related records with spoiler control."""
    name = (name or "").strip()
    if not name:
        return "请提供角色名，例如大卫、露西、丽贝卡、曼恩、亚当重锤。"

    spoiler_level = spoiler_level if spoiler_level in SPOILER_ORDER else "S1"
    matches = []
    blocked_levels = set()
    for item in _load_cyberpunk_chunks():
        text = _chunk_text(item)
        if name not in text:
            continue
        item_level = item.get("spoiler_level", "S1")
        if _spoiler_allowed(item_level, spoiler_level):
            matches.append(item)
        else:
            blocked_levels.add(item_level)

    if matches:
        matches.sort(key=lambda item: (
            0 if item.get("doc_type") == "人物关系与角色解析" else 1,
            SPOILER_ORDER.get(item.get("spoiler_level", "S1"), 1),
        ))
        return "\n\n".join(_format_chunk(item, index + 1) for index, item in enumerate(matches[:5]))

    if blocked_levels:
        levels = "、".join(sorted(blocked_levels, key=lambda level: SPOILER_ORDER.get(level, 99)))
        return f"找到{name}相关资料，但涉及 {levels} 剧透。若你已看完或允许剧透，请提高 spoiler_level。"

    return f"未找到{name}的结构化角色资料。"


@tool(description="根据用户的观影偏好生成《赛博朋克：边缘行者》观看画像与推荐/避雷建议。")
def get_user_profile(viewer_profile: str):
    """Build a viewer preference profile for Cyberpunk: Edgerunners."""
    text = (viewer_profile or "").strip()
    if not text:
        return "请描述你的偏好或雷点，例如：喜欢科幻、怕血腥、没玩过游戏、能不能接受悲剧。"

    positives = []
    cautions = []

    if any(word in text for word in ("赛博朋克", "科幻", "反乌托邦", "夜之城", "银翼杀手")):
        positives.append("你对赛博朋克/科幻/反乌托邦题材有兴趣，题材匹配度高。")
    if any(word in text for word in ("短", "节奏快", "不想长篇", "一口气")):
        positives.append("本作只有 10 集，适合想看短篇高密度故事的观众。")
    if any(word in text for word in ("作画", "视觉", "TRIGGER", "动作", "音乐")):
        positives.append("本作视觉风格、动作演出和音乐记忆点很强，符合制作向偏好。")
    if any(word in text for word in ("悲剧", "致郁", "刀", "压抑")):
        positives.append("如果你主动想看悲剧和高情绪强度作品，本作很对口。")

    if any(word in text for word in ("怕血", "血腥", "暴力", "接受不了")):
        cautions.append("本作包含血腥暴力和身体改造画面，需要谨慎。")
    if any(word in text for word in ("不想哭", "怕刀", "怕致郁", "轻松", "治愈")):
        cautions.append("本作后劲很强，不是轻松治愈向，可能会明显影响情绪。")
    if any(word in text for word in ("没玩过", "没玩游戏", "新手")):
        positives.append("没玩过《Cyberpunk 2077》也能看懂动画主线。")
        cautions.append("部分夜之城术语需要靠剧情理解，刚开始信息量会偏大。")

    if not positives:
        positives.append("如果你能接受成人向、短篇高密度、强风格化叙事，本作值得尝试。")
    if not cautions:
        cautions.append("主要雷点是血腥暴力、精神崩溃、悲剧结局和压抑世界观。")

    return (
        "观影画像：\n"
        + "\n".join(f"- 适合点：{item}" for item in positives)
        + "\n"
        + "\n".join(f"- 避雷点：{item}" for item in cautions)
        + "\n建议：默认先按无剧透方式看前 1-2 集；如果能接受它的情绪强度，再继续。"
    )
