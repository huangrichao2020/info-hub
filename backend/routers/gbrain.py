"""Compatibility gbrain write endpoint.

Hermes cron jobs historically attempted to write gbrain pages through
Info-Hub at /api/gbrain/pages/{slug}/content. The real durable store on
this Mac is the local wiki/gbrain-sync markdown tree, so this endpoint
bridges that old API shape to the current filesystem-backed wiki.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="", tags=["gbrain compatibility"])

WIKI_ROOT = Path.home() / "wiki" / "gbrain-sync"
PUBLISH_SCRIPT = Path.home() / "wiki" / "helpers" / "publish_static_wiki.py"
_SLUG_RE = re.compile(r"[^A-Za-z0-9_.-]+")


class GbrainPageWrite(BaseModel):
    content: str | None = None
    markdown: str | None = None
    text: str | None = None
    mode: str = "append"
    title: str | None = None


def _safe_slug(slug: str) -> str:
    cleaned = _SLUG_RE.sub("-", slug).strip(".-_")
    return cleaned or "untitled"


async def _read_payload(request: Request) -> GbrainPageWrite:
    content_type = request.headers.get("content-type", "")
    raw = await request.body()
    if "application/json" in content_type and raw:
        try:
            data: Any = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            data = {"content": raw.decode("utf-8", errors="replace")}
        if isinstance(data, dict):
            return GbrainPageWrite(**data)
        return GbrainPageWrite(content=str(data))
    return GbrainPageWrite(content=raw.decode("utf-8", errors="replace") if raw else "")


def _publish() -> dict[str, Any]:
    if not PUBLISH_SCRIPT.exists():
        return {"published": False, "reason": "publish script missing"}
    proc = subprocess.run(
        ["python3", str(PUBLISH_SCRIPT)],
        cwd=str(PUBLISH_SCRIPT.parent),
        text=True,
        capture_output=True,
        timeout=90,
    )
    return {
        "published": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }


@router.post("/pages/{slug}/content")
async def write_page_content(slug: str, request: Request):
    payload = await _read_payload(request)
    content = payload.content or payload.markdown or payload.text or ""
    safe_slug = _safe_slug(slug)
    WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    path = WIKI_ROOT / f"{safe_slug}.md"

    if payload.mode == "overwrite" or not path.exists():
        title = payload.title or safe_slug
        body = content.strip()
        path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        action = "overwritten" if payload.mode == "overwrite" else "created"
    else:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        old = path.read_text(encoding="utf-8")
        entry = content.strip()
        if entry and entry not in old:
            path.write_text(old.rstrip() + f"\n\n<!-- updated: {stamp} -->\n" + entry + "\n", encoding="utf-8")
            action = "appended"
        else:
            action = "unchanged"

    publish = _publish()
    return {"status": "ok", "slug": safe_slug, "path": str(path), "action": action, "publish": publish}
