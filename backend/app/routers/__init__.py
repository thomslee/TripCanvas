# -*- coding: utf-8 -*-
from .trips import router as trips_router
from .itinerary import router as itinerary_router
from .poi import router as poi_router
from .weather import router as weather_router

__all__ = ["trips_router", "itinerary_router", "poi_router", "weather_router"]
