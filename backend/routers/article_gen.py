"""文章生成路由 - SSE 流式输出"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.schemas import ArticleRequest
from llm.qwen_client import chat_stream
from llm.prompts import article_messages
from database import get_db

router = APIRouter()


@router.post("/generate")
async def generate(req: ArticleRequest):
    messages = article_messages(req.topic, req.platform, req.reference_material, req.word_count)

    async def event_stream():
        full_content = []
        async for chunk in chat_stream(messages):
            full_content.append(chunk)
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

        # 保存到数据库
        content = "".join(full_content)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO generated_articles (topic, platform, style, content, word_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (req.topic, req.platform, req.style, content, len(content), datetime.now(timezone.utc).isoformat()),
            )
        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
async def history():
    with get_db() as conn:
        rows = conn.execute("SELECT id, topic, platform, word_count, created_at FROM generated_articles ORDER BY created_at DESC LIMIT 50").fetchall()
        return {"items": [dict(r) for r in rows]}


@router.get("/history/{article_id}")
async def detail(article_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM generated_articles WHERE id = ?", (article_id,)).fetchone()
        return dict(row) if row else {"error": "not found"}
