from fastapi import FastAPI, Request
import requests
import os
from openai import OpenAI

app = FastAPI()

ID_INSTANCE = "7107660125"
API_TOKEN = "18af37c556694f5690817d49289b5134c140fa3d9ad49c49b"
BASE_URL = f"https://api.green-api.com/waInstance{ID_INSTANCE}"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/")
async def bot_webhook(request: Request):
    data = await request.json()
    if "messageData" in data and "textMessageData" in data["messageData"]:
        chat_id = data["senderData"]["chatId"]
        user_message = data["messageData"]["textMessageData"]["textMessage"]
        
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
        
        requests.post(f"{BASE_URL}/sendMessage/{API_TOKEN}", json={
            "chatId": chat_id,
            "message": ai_reply
        })
    return {"status": "ok"}
