"""Hermetic provider defaults; individual provider tests explicitly enable mocked calls."""
import os
for key in ('WEATHER_ENABLED','AIR_QUALITY_ENABLED','GEOCODING_ENABLED','EONET_ENABLED','ROUTING_ENABLED','PUSH_NOTIFICATIONS_ENABLED'):
    os.environ[key]='false'
