from fastapi import FastAPI, Request
import requests

app = FastAPI()

# Ваши данные (подставьте сюда свои значения)
ID_INSTANCE = "ВАШ_ID"
API_TOKEN = "ВАШ_TOKEN"
BASE_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}"

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    sender = data['senderData']['chatId']
    message = data['messageData']['textMessageData']['textMessage']

    # Здесь будет логика: 
    # 1. Отправить текст в OpenAI
    # 2. Получить ответ
    # 3. Отправить ответ в WhatsApp через Green-API
    
    print(f"Пришло сообщение от {sender}: {message}")
    return {"status": "ok"}