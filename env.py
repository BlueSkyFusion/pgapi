# pgapi/env.py

"""
env.py

Created on: 2025-07-21
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.1

"""


import os
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

def get_env_var(key: str, length: int = None) -> str:
    value = os.getenv(key)
    if not value:
        raise HTTPException(status_code=500, detail=f"Missing env key: {key}")
    if length and len(value) != length:
        raise HTTPException(status_code=500, detail=f"Invalid env key length: {key}")
    return value

# Strict load of factory key
PIANOGUARD_FACTORY_KEY = get_env_var("PIANOGUARD_FACTORY_KEY", 64)
