"""
main.py

Created on: 2025-07-20
Edited on: 2025-07-21
Author: R. Andrew Ballard (c) 2025 "Andwardo"
Version: v2.0.0
Integrated asyncpg with connection pooling and proper PostgreSQL queries
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from data import router as data_router, init_db_pool, close_db_pool

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database connection pool"""
    # Startup: Initialize database connection pool
    await init_db_pool()
    yield
    # Shutdown: Close database connection pool
    await close_db_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(data_router)


@app.get("/")
async def root():
    return {"message": "PianoGuard API online"}


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PianoGuard API",
        "version": "v2.0.0"
    }


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
