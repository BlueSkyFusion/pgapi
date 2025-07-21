"""
main.py

Created on: 2025-07-20
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.3
Use pgapi.env for environment variable access with strict validation
"""

from fastapi import FastAPI
from pgapi.env import ENVIRONMENT, PIANOGUARD_FACTORY_KEY

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "PianoGuard API online"}


@app.get("/env-test")
async def env_test():
    if ENVIRONMENT == "dev":
        return {"key": PIANOGUARD_FACTORY_KEY}
    return {"error": "Not authorized"}
