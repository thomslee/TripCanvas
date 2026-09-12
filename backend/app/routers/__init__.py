# -*- coding: utf-8 -*-
from .trips import router as trips_router
from .itinerary import router as itinerary_router
from .poi import router as poi_router
from .weather import router as weather_router
from .settings import router as settings_router
from .auth import router as auth_router
from .admin import router as admin_router
from .share import router as share_router

__all__ = ["trips_router", "itinerary_router", "poi_router", "weather_router", "settings_router", "auth_router", "admin_router", "share_router"]
