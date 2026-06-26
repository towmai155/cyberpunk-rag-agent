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

st.markdown(
    """
    <style>
    :root {
        --app-bg: #f6f8fb;
        --surface: #ffffff;
        --surface-subtle: #f9fbff;
        --sidebar: #f1f5fb;
        --ink: #0f1f33;
        --ink-soft: #40546d;
        --muted: #64748b;
        --line: #d7e0ec;
        --line-strong: #b8c7da;
        --blue: #1f6feb;
        --blue-strong: #164da8;
        --blue-soft: #eaf2ff;
        --blue-wash: #f3f7ff;
        --focus: 0 0 0 3px rgba(31, 111, 235, 0.18);
    }

    html, body, [class*="css"] {
        font-family: Inter, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif;
        color: var(--ink);
    }

    .stApp {
        background: var(--app-bg);
    }

    header[data-testid="stHeader"] {
        background: rgba(246, 248, 251, 0.94);
        border-bottom: 1px solid var(--line);
        backdrop-filter: blur(8px);
    }

    .main .block-container {
        max-width: 1120px;
        padding: 1.35rem 2rem 7.2rem;
    }

    .console-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding: 1rem 1.1rem 1.05rem;
        border: 1px solid var(--line);
        border-radius: 10px;
        background: var(--surface);
    }

    .title-group {
        min-width: 0;
    }

    .console-title {
        margin: 0;
        color: var(--ink);
        font-size: 1.38rem;
        line-height: 1.3;
        font-weight: 750;
        letter-spacing: 0;
        text-wrap: balance;
    }

    .console-subtitle {
        margin: 0.35rem 0 0;
        max-width: 68ch;
        color: var(--ink-soft);
        font-size: 0.96rem;
        line-height: 1.65;
        font-weight: 500;
        text-wrap: pretty;
    }

    .status-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.45rem;
        flex: 0 0 auto;
        padding-top: 0.1rem;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.34rem;
        min-height: 1.85rem;
        padding: 0.28rem 0.58rem;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: var(--blue-wash);
        color: var(--blue-strong);
        font-size: 0.82rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .status-dot {
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 999px;
        background: var(--blue);
    }

    .action-zone {
        margin: 0.95rem 0 0.7rem;
        padding-bottom: 0.2rem;
        border-bottom: 1px solid var(--line);
    }

    .shortcut-heading {
        margin: 1.05rem 0 0.35rem;
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 750;
    }

    .side-brand {
        padding: 0.8rem 0.82rem;
        margin-bottom: 0.85rem;
        border: 1px solid var(--line);
        border-radius: 10px;
        background: var(--surface);
    }

    .side-brand-title {
        margin: 0;
        color: var(--ink);
        font-size: 0.98rem;
        font-weight: 750;
    }

    .side-brand-sub {
        margin: 0.28rem 0 0;
        color: var(--ink-soft);
        font-size: 0.84rem;
        line-height: 1.55;
    }

    .section-label {
        margin: 0.75rem 0 0.35rem;
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 750;
    }

    section[data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 750;
        margin-bottom: 0.2rem;
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: var(--muted);
        font-weight: 600;
    }

    div[data-testid="stChatMessage"] {
        margin: 0.72rem 0;
        border-radius: 10px;
        border: 1px solid var(--line) !important;
        background: var(--surface);
        box-shadow: none;
        animation: surfaceIn 0.18s ease-out;
    }

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: var(--surface);
    }

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: var(--surface-subtle);
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
        font-size: 1rem;
        line-height: 1.76;
        color: var(--ink);
        font-weight: 500;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--ink);
        font-weight: 750;
        letter-spacing: 0;
        text-wrap: balance;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] table {
        border-radius: 8px;
        background: var(--surface);
        box-shadow: none;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] thead,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] thead tr {
        background: var(--blue-wash);
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td {
        padding: 0.62rem 0.74rem;
        font-size: 0.94rem;
    }

    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"] {
        transform: scale(0.98);
        border-radius: 8px;
    }

    div[data-testid="stBottom"]::before,
    div[data-testid="stBottomBlockContainer"]::before {
        background: linear-gradient(180deg, rgba(246,248,251,0), rgba(246,248,251,0.96) 42%, var(--app-bg) 100%);
    }

    [data-testid="stChatInput"] {
        width: min(1040px, calc(100% - 1.6rem));
        bottom: 0.82rem;
        background: var(--surface) !important;
        border: 1px solid var(--line-strong);
        border-radius: 12px;
        box-shadow: 0 8px 8px rgba(15, 31, 51, 0.04);
        padding: 0.1rem 0.34rem;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: var(--blue);
        box-shadow: var(--focus);
    }

    [data-testid="stChatInput"] textarea {
        font-size: 1rem;
        color: var(--ink);
        min-height: 2.45rem !important;
        padding: 0.72rem 0.62rem !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #52677f;
        opacity: 1;
    }

    [data-testid="stChatInput"] button:hover {
        background: var(--blue-soft) !important;
        border-radius: 8px;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button {
        min-height: 2.26rem;
        border-radius: 8px;
        border: 1px solid var(--line-strong);
        background: var(--surface);
        color: var(--ink-soft);
        font-weight: 700;
        font-size: 0.9rem;
        box-shadow: none;
        transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stHorizontalBlock"] div[data-testid="column"] .stButton button:hover {
        background: var(--blue-soft);
        border-color: #9fbeeb;
        color: var(--blue-strong);
        transform: none;
        box-shadow: none;
    }

    div[data-testid="stButton"] button[kind="primary"] {
        background: var(--blue);
        border-color: var(--blue);
        color: #ffffff;
        font-weight: 750;
    }

    div[data-testid="stButton"] button[kind="primary"]:hover {
        background: var(--blue-strong);
        border-color: var(--blue-strong);
        color: #ffffff;
    }

    div[data-testid="stButton"] button:focus-visible,
    [data-testid="stChatInput"] button:focus-visible {
        box-shadow: var(--focus) !important;
        outline: none !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 9px;
        border-color: var(--line);
        background: var(--blue-wash);
    }

    .ref-wrap {
        margin-top: 0.9rem;
        padding-top: 0.85rem;
        border-top: 1px solid var(--line);
    }

    .ref-title {
        color: var(--ink-soft);
        font-weight: 750;
    }

    .ref-chip {
        border: 1px solid var(--line);
        background: var(--surface);
        color: var(--blue-strong);
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
    }

    div[data-testid="stExpander"] summary {
        color: var(--ink-soft);
        font-weight: 700;
    }

    @keyframes surfaceIn {
        from {
            transform: translateY(4px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *,
        *::before,
        *::after {
            animation-duration: 0.001ms !important;
            animation-iteration-count: 1 !important;
            scroll-behavior: auto !important;
            transition-duration: 0.001ms !important;
        }
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.85rem 7.2rem;
        }

        .console-header {
            display: block;
            padding: 0.9rem;
        }

        .console-title {
            font-size: 1.2rem;
        }

        .console-subtitle {
            font-size: 0.92rem;
        }

        .status-row {
            justify-content: flex-start;
            margin-top: 0.75rem;
        }

        [data-testid="stChatInput"] {
            width: calc(100% - 0.9rem);
            bottom: 0.45rem;
            border-radius: 10px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    :root {
        --deep: #0b1b34;
        --deep-2: #102a52;
        --paper: #ffffff;
        --blue-line: #c6d8f0;
        --sky: #eef6ff;
        --glow: rgba(31, 111, 235, 0.16);
    }

    .stApp {
        background:
            radial-gradient(circle at 15% -10%, rgba(31, 111, 235, 0.15), transparent 26rem),
            radial-gradient(circle at 100% 4%, rgba(14, 165, 233, 0.12), transparent 22rem),
            linear-gradient(180deg, #f7fbff 0%, #eef4fb 100%);
    }

    .main .block-container {
        max-width: 1200px;
        padding-top: 1rem;
    }

    .workspace-shell {
        border: 1px solid var(--blue-line);
        border-radius: 16px;
        overflow: hidden;
        background: var(--paper);
        box-shadow: 0 18px 30px rgba(16, 42, 82, 0.08);
    }

    .command-bar {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 1rem;
        align-items: center;
        padding: 1rem 1.1rem;
        color: #ffffff;
        background:
            linear-gradient(135deg, var(--deep) 0%, var(--deep-2) 72%, #174ea6 100%);
    }

    .brand-mark {
        display: inline-flex;
        align-items: center;
        gap: 0.62rem;
        min-width: 0;
    }

    .brand-icon {
        width: 2.15rem;
        height: 2.15rem;
        display: inline-grid;
        place-items: center;
        border-radius: 10px;
        background: #ffffff;
        color: var(--blue-strong);
        font-weight: 850;
        letter-spacing: 0;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.22);
    }

    .brand-copy {
        min-width: 0;
    }

    .brand-kicker {
        margin: 0;
        color: #aecaef;
        font-size: 0.76rem;
        font-weight: 700;
    }

    .brand-title {
        margin: 0.08rem 0 0;
        color: #ffffff;
        font-size: 1.22rem;
        line-height: 1.25;
        font-weight: 780;
        letter-spacing: 0;
    }

    .command-meta {
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .command-chip {
        display: inline-flex;
        align-items: center;
        min-height: 1.75rem;
        padding: 0.26rem 0.58rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.1);
        color: #eaf2ff;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .hero-console {
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.55fr);
        gap: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .hero-main {
        padding: 1.25rem 1.25rem 1.15rem;
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    }

    .hero-side {
        padding: 1.1rem;
        border-left: 1px solid var(--blue-line);
        background: #f1f7ff;
    }

    .console-title {
        color: var(--deep);
        font-size: 1.72rem;
        font-weight: 820;
        line-height: 1.22;
    }

    .console-subtitle {
        max-width: 72ch;
        color: #334d6d;
        font-size: 1rem;
    }

    .capability-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.6rem;
        margin-top: 1rem;
    }

    .capability {
        min-height: 4.7rem;
        padding: 0.76rem;
        border: 1px solid var(--blue-line);
        border-radius: 10px;
        background: #ffffff;
    }

    .capability-label {
        margin: 0;
        color: var(--deep);
        font-size: 0.9rem;
        font-weight: 780;
    }

    .capability-value {
        margin: 0.25rem 0 0;
        color: #55708f;
        font-size: 0.82rem;
        line-height: 1.45;
    }

    .side-stat {
        padding: 0.7rem 0;
        border-bottom: 1px solid var(--blue-line);
    }

    .side-stat:first-child {
        padding-top: 0;
    }

    .side-stat:last-child {
        border-bottom: 0;
        padding-bottom: 0;
    }

    .side-stat-k {
        margin: 0;
        color: #55708f;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .side-stat-v {
        margin: 0.18rem 0 0;
        color: var(--deep);
        font-size: 0.98rem;
        font-weight: 800;
    }

    .action-zone {
        margin: 1rem 0 0.65rem;
        padding: 0.72rem;
        border: 1px solid var(--blue-line);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.74);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
    }

    .shortcut-heading {
        margin-top: 1rem;
        padding-left: 0.15rem;
        color: #375a82;
        font-size: 0.86rem;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px;
        border-color: #cfdff2 !important;
        background: rgba(255, 255, 255, 0.92);
        box-shadow: 0 8px 18px rgba(16, 42, 82, 0.05);
    }

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(180deg, #ffffff, #f6faff);
    }

    [data-testid="stChatInput"] {
        width: min(1080px, calc(100% - 2rem));
        border: 1px solid #9fbce2;
        border-radius: 16px;
        box-shadow: 0 16px 30px rgba(16, 42, 82, 0.12);
    }

    section[data-testid="stSidebar"] {
        background: #e9f1fb;
    }

    .side-brand {
        border: 0;
        color: #ffffff;
        background: linear-gradient(135deg, #102a52, #1f6feb);
        box-shadow: 0 12px 22px rgba(16, 42, 82, 0.12);
    }

    .side-brand-title,
    .side-brand-sub {
        color: #ffffff;
    }

    .side-brand-sub {
        color: #dceaff;
    }

    @media (max-width: 900px) {
        .command-bar,
        .hero-console {
            display: block;
        }

        .command-meta {
            justify-content: flex-start;
            margin-top: 0.75rem;
        }

        .hero-side {
            border-left: 0;
            border-top: 1px solid var(--blue-line);
        }

        .capability-grid {
            grid-template-columns: 1fr;
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
    st.markdown(
        """
        <div class="side-brand">
            <p class="side-brand-title">Cyberpunk RAG Agent</p>
            <p class="side-brand-sub">中文作品知识库问答，支持来源追踪和多轮会话。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("## 会话")
    sidebar_action_cols = st.columns(2)
    if sidebar_action_cols[0].button("新建会话", use_container_width=True):
        create_new_chat()
        st.rerun()
    if sidebar_action_cols[1].button("删除当前", use_container_width=True):
        delete_current_chat()
        st.rerun()

    st.markdown('<div class="section-label">历史记录</div>', unsafe_allow_html=True)
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
    <div class="workspace-shell">
        <div class="command-bar">
            <div class="brand-mark">
                <span class="brand-icon">NC</span>
                <div class="brand-copy">
                    <p class="brand-kicker">Cyberpunk RAG Agent</p>
                    <p class="brand-title">Night City Knowledge Console</p>
                </div>
            </div>
            <div class="command-meta">
                <span class="command-chip">Local KB</span>
                <span class="command-chip">Parent-Child</span>
                <span class="command-chip">Ragas 0.8241</span>
            </div>
        </div>
        <div class="hero-console">
            <div class="hero-main">
                <h1 class="console-title">边缘行者知识库助手</h1>
                <p class="console-subtitle">围绕剧情、角色、夜之城设定、音乐电台和游戏联动，给出可追溯的中文解答。适合演示 RAG 检索链路、来源引用和作品内容问答。</p>
                <div class="capability-grid">
                    <div class="capability">
                        <p class="capability-label">混合检索</p>
                        <p class="capability-value">Dense + BM25s/jieba + RRF 融合召回。</p>
                    </div>
                    <div class="capability">
                        <p class="capability-label">上下文回填</p>
                        <p class="capability-value">Child 命中，Parent 生成，减少碎片化。</p>
                    </div>
                    <div class="capability">
                        <p class="capability-label">可信回答</p>
                        <p class="capability-value">回答后展示本地参考来源与片段预览。</p>
                    </div>
                </div>
            </div>
            <div class="hero-side">
                <div class="side-stat">
                    <p class="side-stat-k">Knowledge Domain</p>
                    <p class="side-stat-v">Edgerunners / 2077</p>
                </div>
                <div class="side-stat">
                    <p class="side-stat-k">Spoiler Policy</p>
                    <p class="side-stat-v">S0 - Full</p>
                </div>
                <div class="side-stat">
                    <p class="side-stat-k">Evaluation</p>
                    <p class="side-stat-v">35 Golden Cases</p>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
st.markdown('<div class="action-zone">', unsafe_allow_html=True)
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
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="shortcut-heading">快捷问题</div>', unsafe_allow_html=True)
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
