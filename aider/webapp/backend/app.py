from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.chat import router as chat_router
from .routes.files import router as files_router


def create_app() -> FastAPI:
    app = FastAPI(title="Aider Web API", version="0.1.0")

    # CORS for local frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()