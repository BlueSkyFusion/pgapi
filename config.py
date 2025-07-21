"""
config.py

Created on: 2025-07-21
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.0
Adds typed environment config using Pydantic BaseSettings
"""

from pydantic import BaseSettings, StrictStr

class Settings(BaseSettings):
    ENVIRONMENT: StrictStr = "prod"
    PIANOGUARD_FACTORY_KEY: StrictStr

    class Config:
        env_file = ".env"


settings = Settings()
