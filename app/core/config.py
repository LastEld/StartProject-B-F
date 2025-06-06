# app/core/config.py
"""
This file is created to maintain compatibility with modules
that may be importing settings from `app.core.config`.
The actual settings are defined in `app.core.settings.py`.
"""
from app.core.settings import settings

# Make the settings instance available for import
__all__ = ["settings"]
