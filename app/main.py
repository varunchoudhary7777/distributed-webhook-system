from fastapi import FastAPI

from app.core.config import settings
from app.routers import api_key, auth, project, events

app = FastAPI(title=settings.app_name)

app.include_router(auth.router)
app.include_router(api_key.router)
app.include_router(project.router)
app.include_router(events.router)

@app.get("/health/live", tags=["health"])
async def live():
    return {"status": "alive"}