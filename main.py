import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/")
async def root(request: Request):
    return {"status": "ok"}
