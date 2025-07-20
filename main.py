from fastapi import FastAPI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "PianoGuard API online"}

@app.get("/env-test")
def env_test():
    factory_key = os.getenv("PIANOGUARD_FACTORY_KEY", "MISSING")
    return {"PIANOGUARD_FACTORY_KEY": factory_key}
