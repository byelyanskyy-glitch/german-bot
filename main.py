import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Получаем API ключ. Если его нет, бот выдаст ошибку при запуске, 
# но процесс не упадет сразу.
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

@app.post("/")
async def root(request: Request):
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
