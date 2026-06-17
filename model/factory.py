import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional, Union

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI

from utils.config_handler import rag_conf


class BaseModelFactory(ABC):
    """Base factory for chat and embedding models."""

    @abstractmethod
    def generate(self) -> Optional[Union[Embeddings, BaseChatModel]]:
        pass


class ChatModelFactory(BaseModelFactory):
    """Create the configured chat model."""

    def generate(self) -> BaseChatModel:
        provider = rag_conf.get("chat_model_provider", "dashscope")

        if provider == "deepseek":
            _require_env_var("DEEPSEEK_API_KEY", "DeepSeek chat model")
            return ChatOpenAI(
                model=rag_conf["chat_model_name"],
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com",
            )

        if provider == "dashscope":
            _require_env_var("DASHSCOPE_API_KEY", "DashScope chat model")
            return ChatTongyi(model=rag_conf["chat_model_name"])

        raise ValueError(f"Unsupported chat model provider: {provider}")


class EmbeddingsFactory(BaseModelFactory):
    """Create the configured embedding model."""

    def generate(self) -> Embeddings:
        provider = rag_conf.get("embedding_model_provider", "dashscope")

        if provider == "dashscope":
            _require_env_var("DASHSCOPE_API_KEY", "DashScope embedding model")
            return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])

        raise ValueError(f"Unsupported embedding model provider: {provider}")


def _require_env_var(name: str, label: str) -> None:
    """Check credentials before model initialization."""
    if not os.getenv(name):
        raise EnvironmentError(f"Missing environment variable {name}; cannot initialize {label}.")


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Lazily create and cache the chat model."""
    return ChatModelFactory().generate()


@lru_cache(maxsize=1)
def get_embedding_model() -> Embeddings:
    """Lazily create and cache the embedding model."""
    return EmbeddingsFactory().generate()
