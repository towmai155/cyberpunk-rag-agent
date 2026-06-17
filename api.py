from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException

from agent.react_agent import ReactAgent
from agent.tools.agent_tools import (
    get_character_profile,
    get_episode_summary,
    get_user_profile,
    search_cyberpunk_kb,
)
from rag.rag_service import RagSummarizeService
from utils.bootstrap import validate_runtime


app = FastAPI(
    title="Cyberpunk Edgerunners RAG Agent API",
    version="0.1.0",
    description="Service API for the Cyberpunk: Edgerunners RAG Agent.",
)

agent = ReactAgent()
rag_service = RagSummarizeService()


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class QueryRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    query: str
    spoiler_level: str = "S1"
    max_results: int = 5


class EpisodeRequest(BaseModel):
    episode: int
    spoiler_level: str = "S1"


class CharacterRequest(BaseModel):
    name: str
    spoiler_level: str = "S1"


class ViewerProfileRequest(BaseModel):
    viewer_profile: str


@app.get("/health")
def health():
    issues = validate_runtime()
    return {"ok": not issues, "issues": issues}


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages 不能为空")
    messages = [message.model_dump() for message in request.messages]
    answer = "".join(agent.execute_stream(messages)).strip()
    return {"answer": answer}


@app.post("/rag/query")
def rag_query(request: QueryRequest):
    return {"answer": rag_service.rag_summarize(request.query)}


@app.post("/tools/search")
def tool_search(request: SearchRequest):
    return {
        "result": search_cyberpunk_kb.invoke(
            {
                "query": request.query,
                "spoiler_level": request.spoiler_level,
                "max_results": request.max_results,
            }
        )
    }


@app.post("/tools/episode")
def tool_episode(request: EpisodeRequest):
    return {
        "result": get_episode_summary.invoke(
            {"episode": request.episode, "spoiler_level": request.spoiler_level}
        )
    }


@app.post("/tools/character")
def tool_character(request: CharacterRequest):
    return {
        "result": get_character_profile.invoke(
            {"name": request.name, "spoiler_level": request.spoiler_level}
        )
    }


@app.post("/tools/viewer-profile")
def tool_viewer_profile(request: ViewerProfileRequest):
    return {"result": get_user_profile.invoke({"viewer_profile": request.viewer_profile})}
