from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .config import SLMSettings
from .models import (
    ApproveResponse,
    PendingResponse,
    PromptRequest,
    PromptResponse,
    StatusResponse,
)
from .service import SLMService


def create_app(settings: SLMSettings | None = None) -> FastAPI:
    settings = settings or SLMSettings.from_env()

    app = FastAPI(title="Strategic Liquidity Manager (SLM)")
    service = SLMService(settings=settings)
    app.state.slm = service

    @app.on_event("startup")
    async def _startup() -> None:
        await service.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await service.stop()

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/status", response_model=StatusResponse)
    async def status() -> StatusResponse:
        return service.get_status()

    @app.get("/pending", response_model=PendingResponse)
    async def pending() -> PendingResponse:
        return service.get_pending()

    @app.post("/prompt", response_model=PromptResponse)
    async def prompt(req: PromptRequest) -> PromptResponse:
        req_id = await service.enqueue_prompt(req.prompt)
        return PromptResponse(id=req_id, state=service.requests[req_id].state)

    @app.post("/approve/{req_id}", response_model=ApproveResponse)
    async def approve(req_id: str) -> ApproveResponse:
        ok = await service.approve(req_id)
        if not ok:
            raise HTTPException(status_code=404, detail="No pending request with that id")
        return ApproveResponse(id=req_id, state=service.requests[req_id].state)

    @app.post("/deny/{req_id}", response_model=ApproveResponse)
    async def deny(req_id: str) -> ApproveResponse:
        ok = await service.deny(req_id)
        if not ok:
            raise HTTPException(status_code=404, detail="No pending request with that id")
        return ApproveResponse(id=req_id, state=service.requests[req_id].state)

    return app


app = create_app()
