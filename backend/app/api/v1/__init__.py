from fastapi import APIRouter

from app.api.v1 import papers, subscribe, rss

api_router = APIRouter()
api_router.include_router(papers.router, tags=["papers"])
api_router.include_router(subscribe.router, tags=["subscription"])
api_router.include_router(rss.router, tags=["rss"])
