import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Ваши настройки
ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

# Инициализация клиента OpenAI (API ключ берется из настроек Render)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    
    # Проверяем, что это входящее сообщение и в нем есть текст
    if (data.get("typeWebhook") == "incomingMessageReceived" and 
        "messageData" in data and 
        "textMessageData" in data["messageData"]):
        
        chat_id = data["senderData"]["chatId"]
        user_message = data["messageData"]["textMessageData"]["textMessage"]
        
        # Запрос к ChatGPT
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """
Ты — профессиональный преподаватель немецкого языка. 
Твоя цель: помогать ученикам уровня А1-В1. 
Твои правила:
1. Если ученик просит упражнение, дай ему короткий тест или задачу по грамматике/лексике.
2. Проверяй ответы ученика, указывай на ошибки и объясняй их.
3. Поддерживай общение на двух языках: если ученик пишет на русском/украинском, отвечай на этом языке, но обязательно добавляй фразы на немецком для обучения.
4. Будь вежливым, поддерживающим и мотивирующим.
"""},
                    {"role": "user", "content": user_message}
                ]
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = "Извините, произошла ошибка при общении с ИИ."
            print(f"Ошибка OpenAI: {e}")
        
        # Отправка ответа в WhatsApp
        requests.post(f"{BASE_URL}/sendMessage/{API_TOKEN}", json={
            "chatId": chat_id,
            "message": ai_reply
        })
        
    return {"status": "ok"}
