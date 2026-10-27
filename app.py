"""Single-user local FastAPI app. No outbound network integrations or arbitrary file paths."""

import os
from contextlib import contextmanager
from pathlib import Path

from core import Workspace
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).parent


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=150)
    text: str = Field(min_length=20, max_length=30000)


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=1000)


class PlanInput(Question):
    minutes: int = Field(ge=10, le=120, strict=True)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: str


def create_app(filename=None):
    filename = filename or os.environ.get("ST_DB_PATH", str(ROOT / "local-data/studytrace.db"))
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    Workspace(filename).close()
    api = FastAPI(title="StudyTrace", docs_url=None, redoc_url=None)
    api.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @contextmanager
    def workspace():
        w = Workspace(filename)
        try:
            yield w
        finally:
            w.close()

    @api.middleware("http")
    async def protect(request, call_next):
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("origin")
            if origin and origin != "http://" + request.headers.get("host", ""):
                return JSONResponse({"detail": "Cross-origin writes are not permitted"}, status_code=403)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"detail": "Use application/json"}, status_code=415)
            # Bound the actual received body, even when a Content-Length header is missing or forged.
            body = bytearray()
            async for part in request.stream():
                body.extend(part)
                if len(body) > 160000:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
            request._body = bytes(body)
        try:
            response = await call_next(request)
        except (ValueError, KeyError) as error:
            return JSONResponse(
                {"detail": str(error).strip("'")}, status_code=400 if isinstance(error, ValueError) else 404
            )
        except Exception:
            return JSONResponse(
                {"detail": "Local operation failed; private diagnostics are not exposed"}, status_code=500
            )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @api.get("/api/stats")
    def stats():
        with workspace() as w:
            return w.stats()

    @api.get("/api/documents")
    def documents():
        with workspace() as w:
            return w.documents()

    @api.post("/api/documents", status_code=201)
    def add_document(value: Note):
        with workspace() as w:
            return w.add_document(value.title, value.text)

    @api.delete("/api/documents/{doc_id}")
    def delete_document(doc_id: str):
        with workspace() as w:
            if not w.delete_document(doc_id):
                raise HTTPException(404, "Document not found")
            return {"deleted": True}

    @api.post("/api/ask")
    def ask(value: Question):
        with workspace() as w:
            return w.ask(value.question)

    @api.get("/api/plans")
    def plans():
        with workspace() as w:
            return w.plans()

    @api.post("/api/plans", status_code=201)
    def plan(value: PlanInput):
        with workspace() as w:
            return w.create_plan(value.question, value.minutes)

    @api.get("/api/plans/{pid}")
    def get_plan(pid: str):
        with workspace() as w:
            return w.get_plan(pid)

    @api.post("/api/plans/{pid}/tasks/{tid}/review")
    def review(pid: str, tid: str, value: ReviewInput):
        with workspace() as w:
            return w.review(pid, tid, value.rating)

    @api.get("/api/plans/{pid}/export")
    def export(pid: str):
        with workspace() as w:
            result = w.get_plan(pid)
        return JSONResponse(
            result, headers={"Content-Disposition": 'attachment; filename="studytrace-plan.json"'}
        )

    @api.get("/")
    def index():
        return FileResponse(ROOT / "web/index.html")

    for name, mime in (("app.js", "application/javascript"), ("style.css", "text/css")):
        # Defaults are captured by the closure; no client-supplied path or query argument is accepted.
        def factory(filename, content_type):
            def serve():
                return FileResponse(ROOT / "web" / filename, media_type=content_type)

            return serve

        api.add_api_route("/" + name, factory(name, mime), methods=["GET"])
    return api


app = create_app()
