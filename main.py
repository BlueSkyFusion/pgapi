"""
main.py

Created on: 2025-07-20
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v1.0.4
Stubbed /register-device route with factory_key validation against env var
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

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


class DeviceRegistration(BaseModel):
    factory_key: str
    serial: str


@app.post("/register-device")
async def register_device(payload: DeviceRegistration):
    expected_key = os.getenv("PIANOGUARD_FACTORY_KEY")

    if payload.factory_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid factory key")

    return {
        "status": "ok",
        "message": f"Device {payload.serial} accepted for registration (stub)."
    }
