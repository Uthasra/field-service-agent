"""HTTP surface. Run: uvicorn app.main:app --reload"""
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.agent import run_turn
from app.config import ROOT
from app.db import connect, init_db

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("fsa")

app = FastAPI(title="Field Service Agent", version="0.1.0")
STATIC = ROOT / "app" / "static"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    trace: list[dict]
    blocked: list[dict]


@app.on_event("startup")
def startup() -> None:
    init_db()
    log.info("database ready")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/assets")
def assets() -> dict:
    conn = connect()
    rows = conn.execute("SELECT * FROM assets ORDER BY asset_id").fetchall()
    conn.close()
    return {"assets": [dict(r) for r in rows]}


@app.get("/work-orders")
def work_orders() -> dict:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM work_orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"work_orders": [dict(r) for r in rows]}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    turn = run_turn(req.message, history=req.history)
    if turn.blocked:
        log.warning("guardrail fired: %s", turn.blocked)
    return ChatResponse(reply=turn.reply, trace=turn.trace, blocked=turn.blocked)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
