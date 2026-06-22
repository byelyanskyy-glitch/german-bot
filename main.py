import os
import requests
import logging
from fastapi import FastAPI, Request
from openai import OpenAI

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Замените на ваши данные
ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI успешно запущен и готов принимать сообщения")

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    logger.info(f"Получено событие: {data}")
    
    # Обработка входящего сообщения
    if data.get("typeWebhook") == "incomingMessageReceived":
        chat_id = data["senderData"]["chatId"]
        user_message = data["messageData"]["textMessageData"]["textMessage"]
        
        # Запрос к OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Ты мультиязычный учитель немецкого. Отвечай на языке пользователя."},
                      {"role": "user", "content": user_message}]
        )
        ai_reply = response.choices[0].message.content
        
        # Отправка ответа в WhatsApp
        requests.post(f"{BASE_URL}/sendMessage/{API_TOKEN}", json={
            "chatId": chat_id,
            "message": ai_reply
        })
        
    return {"status": "ok"}
