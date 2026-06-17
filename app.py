import streamlit as st
from agent.react_agent import ReactAgent
from agent.tools.agent_tools import rag as rag_service
from utils.bootstrap import validate_runtime
from utils.chat_session_store import (
    create_session,
    delete_session,
    load_sessions,
    save_sessions,
    sort_sessions,
    update_session_messages,
    upsert_session,
)
from utils.file_handler import clean_text, pdf_loader
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
import re


st.set_page_config(
    page_title="边缘行者知识库助手",
    page_icon="🌃",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&display=swap');

    :root {
        --ink: #102033;
        --muted: #5f7288;
        --page: #f6f9ff;
        --panel: #ffffff;
        --panel-blue: #eef6ff;
        --line: #d8e5f5;
        --line-strong: #bad3f0;
        --blue: #2563eb;
        --blue-strong: #174ea6;
        --blue-soft: #e7f0ff;
        --cyan: #0ea5e9;
        --shadow: 0 18px 42px rgba(37, 99, 235, 0.09);
    }

    html, body, [class*="css"] {
        font-family: 'Noto Sans SC', sans-serif;
        color: var(--ink);
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
    }

    .stApp {
        background:
            radial-gradient(circle at 82% 0%, rgba(37, 99, 235, 0.12), transparent 31rem),
            linear-gradient(180deg, #fbfdff 0%, var(--page) 45%, #f1f6ff 100%);
    }

    header[data-testid="stHeader"] {
        background: rgba(251, 253, 255, 0.88);
        border-bottom: 1px solid rgba(216, 229, 245, 0.8);
        backdrop-filter: blur(12px);
    }

    [data-testid="stToolbar"] {
        color: var(--ink);
    }

    .main .block-container {
        max-width: 1060px;
        padding-top: 1.8rem;
        padding-bottom: 6.5rem;
    }

    .hero-wrap {
        position: relative;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 1.25rem 1.35rem 1.15rem;
        background:
            linear-gradient(135deg, rgba(37, 99, 235, 0.08), transparent 42%),
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,255,0.96));
        box-shadow: var(--shadow);
        animation: panelIn 0.36s ease-out;
    }

    .hero-wrap::before {
        content: "";
        position: absolute;
        inset: 0 0 auto 0;
        height: 3px;
        background: linear-gradient(90deg, var(--blue), var(--cyan));
    }

    .hero-title {
        margin: 0;
        color: var(--ink);
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1.24;
        letter-spacing: 0;
    }

    .hero-sub {
        margin: 0.35rem 0 0;
        color: var(--muted);
        font-size: 1rem;
        font-weight: 500;
    }

    .stat {
        margin-top: 0.85rem;
        display: inline-block;
        padding: 0.32rem 0.68rem;
        border-radius: 999px;
        border: 1px solid var(--line-strong);
        background: rgba(255,255,255,0.86);
        color: var(--blue-strong);
        font-size: 0.82rem;
        font-weight: 800;
        margin-right: 0.45rem;
    }

    section[data-testid="stSidebar"] {
        background: #f8fbff;
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: var(--ink);
        font-size: 1.18rem;
        font-weight: 800;
        letter-spacing: 0;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--muted);
        font-weight: 700;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.06);
        animation: panelIn 0.28s ease-out;
    }

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: #ffffff;
        border-left: 3px solid #8cb9ff;
    }

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(180deg, #ffffff, #fbfdff);
        border-left: 3px solid var(--blue);
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
        font-size: 1.02rem;
        line-height: 1.78;
        color: var(--ink);
        font-weight: 500;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--ink);
        letter-spacing: 0;
        font-weight: 800;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] table {
        width: 100%;
        margin: 0.75rem 0 1rem;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 10px;
        background: #ffffff;
        color: var(--ink);
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.05);
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] thead,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] thead tr {
        background: #eaf3ff;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td {
        padding: 0.68rem 0.78rem;
        border-bottom: 1px solid var(--line);
        color: var(--ink) !important;
        font-size: 0.96rem;
        line-height: 1.62;
        vertical-align: top;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th {
        color: var(--blue-strong) !important;
        font-weight: 800;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] tbody tr:nth-child(even) {
        background: #f7fbff;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] tbody tr:last-child td {
        border-bottom: 0;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span {
        color: inherit;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code {
        color: var(--blue-strong);
        background: var(--blue-soft);
        border-radius: 6px;
        padding: 0.08rem 0.28rem;
    }

    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"] {
        transform: scale(1.08);
        border-radius: 10px;
    }

    div[data-testid="stBottom"],
    div[data-testid="stBottomBlockContainer"],
    div[data-testid="stChatFloatingInputContainer"] {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stBottom"]::before,
    div[data-testid="stBottomBlockContainer"]::before {
        content: "";
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        height: 5.6rem;
        pointer-events: none;
        background: linear-gradient(180deg, rgba(246,249,255,0), rgba(246,249,255,0.94) 35%, #f6f9ff 100%);
    }

    [data-testid="stChatInput"] {
        position: fixed;
        left: 50%;
        transform: translateX(-50%);
        bottom: 0.85rem;
        width: min(1020px, calc(100% - 1.6rem));
        background: #ffffff !important;
        border: 1px solid var(--line-strong);
        border-radius: 14px;
        box-shadow: 0 16px 34px rgba(37,99,235,0.14);
        padding: 0.16rem 0.42rem;
        backdrop-filter: blur(10px);
        overflow: hidden;
    }

    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] div,
    [data-testid="stChatInput"] section,
    [data-testid="stChatInput"] form {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }

    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        font-size: 1.02rem;
        font-weight: 500;
        color: var(--ink);
        min-height: 2.5rem !important;
        padding: 0.72rem 0.65rem !important;
        box-shadow: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #6b7f97;
        opacity: 1;
    }

    [data-testid="stChatInput"] button {
        background: transparent !important;
        border: 0 !important;
        color: var(--blue) !important;
        box-shadow: none !important;
        min-width: 2.8rem;
    }

    [data-testid="stChatInput"] button:hover {
        background: var(--blue-soft) !important;
        color: var(--blue-strong) !important;
        border-radius: 10px;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button {
        width: 100%;
        min-height: 2.38rem;
        border-radius: 10px;
        border: 1px solid var(--line-strong);
        background: #ffffff;
        color: var(--blue-strong);
        font-weight: 800;
        font-size: 0.92rem;
        box-shadow: 0 6px 14px rgba(37,99,235,0.05);
        transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button:hover {
        background: var(--blue-soft);
        border-color: #8bb8ff;
        color: var(--blue-strong);
        transform: translateY(-1px);
        box-shadow: 0 10px 20px rgba(37,99,235,0.1);
    }

    div[data-testid="stButton"] button[kind="primary"] {
        background: var(--blue);
        border-color: var(--blue);
        color: #ffffff;
    }

    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: var(--blue-strong);
        border-color: var(--blue-strong);
        color: #ffffff;
    }

    div[data-testid="stAlert"] p {
        color: var(--ink);
        font-size: 0.98rem;
        font-weight: 600;
    }

    div[data-testid="stAlert"] {
        border-radius: 12px;
        border-color: var(--line);
        background: #f3f8ff;
    }

    .ref-wrap {
        margin-top: 0.85rem;
        padding-top: 0.8rem;
        border-top: 1px dashed var(--line-strong);
    }

    .ref-title {
        margin-bottom: 0.45rem;
        color: var(--muted);
        font-size: 0.88rem;
        font-weight: 800;
        letter-spacing: 0;
    }

    .ref-chip {
        display: inline-block;
        margin: 0 0.45rem 0.45rem 0;
        padding: 0.3rem 0.6rem;
        border-radius: 999px;
        border: 1px solid var(--line-strong);
        background: #f4f8ff;
        color: var(--blue-strong);
        font-size: 0.84rem;
        font-weight: 700;
        line-height: 1.3;
    }

    .ref-preview {
        margin-top: 0.2rem;
        color: var(--ink);
        font-size: 0.96rem;
        line-height: 1.75;
    }

    @keyframes panelIn {
        from {
            transform: translateY(8px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1.2rem;
            padding-bottom: 7.2rem;
        }

        .hero-title {
            font-size: 1.56rem;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            font-size: 1rem;
            line-height: 1.78;
        }

        [data-testid="stChatInput"] {
            width: calc(100% - 0.9rem);
            bottom: 0.4rem;
            border-radius: 12px;
            padding: 0.2rem 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

runtime_issues = validate_runtime()
if runtime_issues:
    for issue in runtime_issues:
        st.error(issue)
    st.stop()

# Agent 实例只初始化一次，避免每次重跑页面都重新构建模型和工具。
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# sessions 存的是全部历史会话；current_session_id 指向当前打开的那一个。
if "sessions" not in st.session_state:
    sessions = sort_sessions(load_sessions())
    if not sessions:
        sessions = [create_session()]
        save_sessions(sessions)
    st.session_state["sessions"] = sessions

if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = st.session_state["sessions"][0]["id"]

if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = ""


def get_current_session() -> dict:
    """根据 current_session_id 取当前会话；如果丢失则兜底创建一个新会话。"""
    current_session_id = st.session_state["current_session_id"]
    for session in st.session_state["sessions"]:
        if session["id"] == current_session_id:
            return session
    fallback = create_session()
    st.session_state["sessions"] = [fallback] + st.session_state["sessions"]
    st.session_state["current_session_id"] = fallback["id"]
    save_sessions(sort_sessions(st.session_state["sessions"]))
    return fallback


def persist_current_messages(messages: list[dict]) -> None:
    """把当前会话消息写回内存和本地文件。"""
    current = get_current_session()
    updated = update_session_messages(current, messages)
    st.session_state["sessions"] = sort_sessions(upsert_session(st.session_state["sessions"], updated))
    st.session_state["current_session_id"] = updated["id"]
    save_sessions(st.session_state["sessions"])


def switch_session(session_id: str) -> None:
    """切换当前会话，同时清空待发送的快捷问题。"""
    st.session_state["current_session_id"] = session_id
    st.session_state["pending_prompt"] = ""


def create_new_chat() -> None:
    """创建新会话并立即切过去。"""
    new_session = create_session()
    st.session_state["sessions"] = sort_sessions(upsert_session(st.session_state["sessions"], new_session))
    st.session_state["current_session_id"] = new_session["id"]
    st.session_state["pending_prompt"] = ""
    save_sessions(st.session_state["sessions"])


def delete_current_chat() -> None:
    """删除当前会话；如果删完为空，则自动补一个空会话。"""
    current_id = st.session_state["current_session_id"]
    sessions = delete_session(st.session_state["sessions"], current_id)
    if not sessions:
        sessions = [create_session()]
    sessions = sort_sessions(sessions)
    st.session_state["sessions"] = sessions
    st.session_state["current_session_id"] = sessions[0]["id"]
    st.session_state["pending_prompt"] = ""
    save_sessions(sessions)


def split_response_and_references(content: str) -> tuple[str, list[str]]:
    """
    把回答正文和“参考来源”拆开。

    RAG 最终返回的是一段完整文本，这里按约定格式拆分，
    方便前端把正文和引用来源分开展示。
    """
    if not content:
        return "", []

    match = re.search(r"\n参考来源：\s*\n(?P<refs>(?:- .+\n?)*)$", content.strip())
    if not match:
        return content.strip(), []

    body = content[: match.start()].strip()
    refs_block = match.group("refs")
    references = [line[2:].strip() for line in refs_block.splitlines() if line.startswith("- ")]
    return body, references


def render_references(references: list[str]):
    """把引用来源渲染成标签，并支持展开查看预览片段。"""
    if not references:
        return

    chips = "".join(f'<span class="ref-chip">{reference}</span>' for reference in references)
    st.markdown(
        f"""
        <div class="ref-wrap">
            <div class="ref-title">参考来源</div>
            <div>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for index, reference in enumerate(references, start=1):
        with st.expander(f"查看片段 {index}: {reference}", expanded=False):
            st.caption("命中的本地知识片段预览")
            st.write(load_reference_preview(reference))


def parse_reference_label(reference: str) -> tuple[str, int | None]:
    """从“文件名 / 文件名 + 页码”格式中解析出来源和页码。"""
    match = re.match(r"^(?P<source>.+?)(?: 第(?P<page>\d+)页)?$", reference.strip())
    if not match:
        return reference.strip(), None
    source = match.group("source").strip()
    page = match.group("page")
    return source, int(page) - 1 if page else None


@st.cache_data(show_spinner=False)
def load_reference_preview(reference: str) -> str:
    """
    读取引用来源的本地预览片段。

    txt 直接读取文件开头片段；
    pdf 优先按页码读取对应页内容。
    """
    source, page = parse_reference_label(reference)
    abs_path = get_abs_path(f"data/{source}")
    if not abs_path or not source:
        return "未能解析参考来源。"

    try:
        if source.lower().endswith(".txt"):
            with open(abs_path, "r", encoding="utf-8") as f:
                preview = clean_text(f.read())[:420]
                return preview or "该文本来源没有可展示的预览内容。"
        if source.lower().endswith(".pdf"):
            docs = pdf_loader(abs_path)
            if page is not None and 0 <= page < len(docs):
                return clean_text(docs[page].page_content)[:420] or "该页没有可展示内容。"
            if docs:
                return clean_text(docs[0].page_content)[:420] or "PDF 没有可展示内容。"
            return "PDF 没有可展示内容。"
    except FileNotFoundError:
        return f"本地未找到来源文件：{source}"
    except Exception as e:
        logger.warning(f"加载参考片段失败: {reference}, error={str(e)}")
        return f"无法读取该来源的片段预览：{source}"

    return f"当前仅支持预览 txt/pdf 来源，文件：{source}"


def render_message(message: dict):
    """统一渲染一条消息，自动处理正文和引用来源。"""
    body, references = split_response_and_references(message["content"])
    st.write(body or message["content"])
    render_references(references)


with st.sidebar:
    # 侧边栏负责会话管理，体验上接近常见大模型产品的历史会话区。
    st.markdown("## 会话管理")
    sidebar_action_cols = st.columns(2)
    if sidebar_action_cols[0].button("新建会话", use_container_width=True):
        create_new_chat()
        st.rerun()
    if sidebar_action_cols[1].button("删除当前", use_container_width=True):
        delete_current_chat()
        st.rerun()

    st.caption("历史会话")
    current_session = get_current_session()
    for session in st.session_state["sessions"]:
        label = session["title"] or "新对话"
        if st.button(
            label,
            key=f"session_{session['id']}",
            use_container_width=True,
            type="primary" if session["id"] == current_session["id"] else "secondary",
        ):
            switch_session(session["id"])
            st.rerun()

st.markdown(
    """
    <div class="hero-wrap">
        <h1 class="hero-title">边缘行者知识库助手</h1>
        <p class="hero-sub">围绕剧情、角色、夜之城设定、音乐电台和游戏联动，给出可追溯的中文解答。</p>
        <span class="stat">知识检索</span>
        <span class="stat">剧透控制</span>
        <span class="stat">Ragas评测</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
action_cols = st.columns([1, 1, 4])
if action_cols[0].button("清空会话"):
    # 清空的是“当前会话”的消息，不影响其他历史会话。
    persist_current_messages([])
    st.session_state["pending_prompt"] = ""
    st.rerun()

if action_cols[1].button("重建知识库"):
    try:
        with st.spinner("正在重建知识库，请稍候..."):
            # 这里直接调用当前运行中的 RAG 服务实例，避免页面重启后才生效。
            rag_service.vector_store.reset_store(clear_md5=True)
            rag_service.vector_store.load_document(force_reload=True)
            rag_service._collection_ready_checked = True
        st.success("知识库重建完成。")
    except Exception as e:
        logger.error(f"知识库重建失败: {str(e)}", exc_info=True)
        st.error("知识库重建失败，请查看日志。")

shortcut_cols = st.columns(3)
shortcuts = [
    "没玩过游戏能直接看边缘行者吗？",
    "I Really Want to Stay at Your House 出自哪个电台？",
    "露西和大卫的关系为什么让人难受？",
]
for col, text in zip(shortcut_cols, shortcuts):
    if col.button(text):
        st.session_state["pending_prompt"] = text

current_session = get_current_session()
current_messages = current_session.get("messages", [])

# 页面展示的始终是“当前会话”的消息。
if not current_messages:
    st.info("可以先试试上面的快捷问题，也可以直接询问剧情、角色、设定、音乐或联动内容。")

for message in current_messages:
    avatar = "🧑" if message["role"] == "user" else "🌃"
    with st.chat_message(message["role"], avatar=avatar):
        render_message(message)

input_prompt = st.chat_input("请输入你的问题，例如：没玩过 2077 能看边缘行者吗？")
prompt = input_prompt or st.session_state.get("pending_prompt", "")
if prompt:
    st.session_state["pending_prompt"] = ""
    with st.chat_message("user", avatar="🧑"):
        st.write(prompt)
    # 先写入用户消息，再调用 Agent，这样异常时也能保留用户输入。
    current_messages = current_messages + [{"role": "user", "content": prompt}]
    persist_current_messages(current_messages)

    response_chunks = []

    def capture(generator, cache_list, placeholder):
        """一边接收流式输出，一边实时刷新前端占位区域。"""
        for chunk in generator:
            cache_list.append(chunk)
            body, _ = split_response_and_references("".join(cache_list))
            placeholder.markdown(body or "".join(cache_list))
            yield chunk

    try:
        with st.spinner("正在分析问题并检索答案..."):
            res_stream = st.session_state["agent"].execute_stream(current_messages)
            with st.chat_message("assistant", avatar="🌃"):
                response_placeholder = st.empty()
                for _ in capture(res_stream, response_chunks, response_placeholder):
                    pass

        response_text = "".join(response_chunks).strip()
        if not response_text:
            response_text = "暂时没有生成有效回答，请重试。"
        else:
            # 流式阶段只先展示正文，结束后再补渲染来源区，避免中途闪烁。
            body, references = split_response_and_references(response_text)
            response_placeholder.markdown(body or response_text)
            render_references(references)
    except Exception as e:
        logger.error(f"对话处理失败: {str(e)}", exc_info=True)
        response_text = "服务暂时不可用，请稍后重试。"
        with st.chat_message("assistant", avatar="🌃"):
            st.write(response_text)

    # 最终回答也要落盘，这样刷新页面后仍能恢复完整会话。
    current_messages = current_messages + [{"role": "assistant", "content": response_text}]
    persist_current_messages(current_messages)
    st.rerun()
