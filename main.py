import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Ваши данные (лучше в будущем хранить в переменных окружения, но для начала оставим так)
ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}"

# Инициализация OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    
    # Логируем входящие данные, чтобы видеть их в консоли Render
    print("Получены данные:", data)
    
    # Проверка на входящее текстовое сообщение
    if (data.get("typeWebhook") == "incomingMessageReceived" and 
        "messageData" in data and 
        "textMessageData" in data["messageData"]):
        
        chat_id = data["senderData"]["chatId"]
        user_message = data["messageData"]["textMessageData"]["textMessage"]
        
        try:
            # Запрос к ChatGPT
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Ты — преподаватель немецкого языка (А1-В1). Отвечай на языке пользователя, помогай с изучением, давай упражнения по запросу, исправляй ошибки, будь вежлив."},
                    {"role": "user", "content": user_message}
                ]
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = "Извините, возникла техническая ошибка."
            print(f"Ошибка OpenAI: {e}")
        
        # Отправка ответа через Green-API
        requests.post(f"{BASE_URL}/sendMessage/{API_TOKEN}", json={
            "chatId": chat_id,
            "message": ai_reply
        })
        
    return {"status": "ok"}
