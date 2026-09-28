from fastapi import FastAPI

from backend.api.routers.research import router

app = FastAPI(title="ai_trader")
app.include_router(router)
