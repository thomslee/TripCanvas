# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import trips_router, itinerary_router, poi_router, weather_router, settings_router, auth_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="旅游行程智能规划系统后端 API",
)

# 前端 dev server（Vite 默认 5173）与后续部署域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地开发放开，部署时收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips_router)
app.include_router(itinerary_router)
app.include_router(poi_router)
app.include_router(weather_router)
app.include_router(settings_router)
app.include_router(auth_router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
