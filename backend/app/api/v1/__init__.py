from fastapi import APIRouter
from app.api.v1.endpoints import auth, notices, avls, scheduling, incidents, dashboard, ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(notices.router)
api_router.include_router(avls.router)
api_router.include_router(scheduling.router)
api_router.include_router(incidents.router)
api_router.include_router(dashboard.router)
api_router.include_router(ws.router)
