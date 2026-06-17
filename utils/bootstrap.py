import os

from utils.config_handler import chroma_conf, prompts_conf, rag_conf
from utils.path_tool import get_abs_path


def validate_runtime() -> list[str]:
    """
    Startup checks.

    Return a list of issues. An empty list means the current runtime is ready.
    """
    issues = []

    chat_provider = rag_conf.get("chat_model_provider", "dashscope")
    embedding_provider = rag_conf.get("embedding_model_provider", "dashscope")

    if chat_provider == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
        issues.append("缺少环境变量 DEEPSEEK_API_KEY，请先在运行环境中配置后再启动应用。")
    elif chat_provider == "dashscope" and not os.getenv("DASHSCOPE_API_KEY"):
        issues.append("缺少环境变量 DASHSCOPE_API_KEY，当前聊天模型需要该 Key。")
    elif chat_provider not in {"deepseek", "dashscope"}:
        issues.append(f"暂不支持的聊天模型提供方: {chat_provider}")

    if embedding_provider == "dashscope" and not os.getenv("DASHSCOPE_API_KEY"):
        issues.append("缺少环境变量 DASHSCOPE_API_KEY，当前向量模型需要该 Key。")
    elif embedding_provider != "dashscope":
        issues.append(f"暂不支持的向量模型提供方: {embedding_provider}")

    required_paths = [
        ("主提示词", prompts_conf.get("main_prompt_path")),
        ("RAG 提示词", prompts_conf.get("rag_summarize_prompt_path")),
        ("知识库目录", chroma_conf.get("data_path")),
    ]
    for label, relative_path in required_paths:
        if not relative_path:
            issues.append(f"{label}未在配置中声明。")
            continue
        abs_path = get_abs_path(relative_path)
        if not os.path.exists(abs_path):
            issues.append(f"{label}不存在: {abs_path}")

    for key in ("chat_model_name", "embedding_model_name"):
        if not rag_conf.get(key):
            issues.append(f"模型配置缺失: {key}")

    for key in ("collection_name", "persist_directory", "data_path", "md5_hex_store"):
        if not chroma_conf.get(key):
            issues.append(f"向量库配置缺失: {key}")

    prompt_keys = (
        prompts_conf.get("main_prompt_path"),
        prompts_conf.get("rag_summarize_prompt_path"),
    )
    for relative_path in prompt_keys:
        if not relative_path:
            continue
        abs_path = get_abs_path(relative_path)
        if not os.path.exists(abs_path):
            continue
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError:
            issues.append(f"提示词文件不是 UTF-8 编码: {abs_path}")

    return issues
