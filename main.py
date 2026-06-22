import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Инициализация клиента OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    # Логирование для отладки
    print(f"Пришло уведомление: {data}")
    
    if data.get("typeWebhook") == "incomingMessageReceived":
        chat_id = data["senderData"]["chatId"]
        user_message = data["messageData"]["textMessageData"]["textMessage"]
        
        # Запрос к AI
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "Ты учитель немецкого."},
                          {"role": "user", "content": user_message}]
            )
            ai_reply = response.choices[0].message.content
            
            # Отправка в WhatsApp
            requests.post(f"{BASE_URL}/sendMessage/{API_TOKEN}", json={
                "chatId": chat_id,
                "message": ai_reply
            })
        except Exception as e:
            print(f"Ошибка: {e}")
            
    return {"status": "ok"}
