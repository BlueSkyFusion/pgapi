"""
main.py

Created on: 2025-07-20
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.2
Added /env-test route (dev-only) to verify .env key loading
"""

import os
from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "PianoGuard API online"}


@app.get("/env-test")
async def env_test():
    if os.getenv("ENVIRONMENT") == "dev":
        factory_key = os.getenv("PIANOGUARD_FACTORY_KEY")
        return {"key": factory_key}
    return {"error": "Not authorized"}
