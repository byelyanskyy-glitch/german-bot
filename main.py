import os
import logging
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ---------------- FASTAPI ----------------
app = FastAPI()

# ---------------- ENV ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GREEN_API_INSTANCE_ID = os.getenv("7107660125")
GREEN_API_TOKEN = os.getenv("18af37c556694f5690817d49d289b5134c140fa3d9ad49c49b")
GREEN_API_URL = os.getenv("https://api.green-api.com/waInstance{ID_INSTANCE}", "https://api.green-api.com")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- HEALTH ----------------
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"ok": True}

# ---------------- SEND MESSAGE TO WHATSAPP ----------------
def send_whatsapp_message(chat_id: str, text: str):
    url = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"

    payload = {
        "chatId": chat_id,
        "message": text
    }

    response = requests.post(url, json=payload, timeout=10)

    logger.info(f"Green-API response: {response.status_code} {response.text}")

    return response.json()

# ---------------- WEBHOOK ----------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Incoming: {data}")

        message_data = data.get("messageData", {})
        text = message_data.get("textMessageData", {}).get("textMessage")

        sender = data.get("senderData", {})
        chat_id = sender.get("chatId")

        if not text or not chat_id:
            return {"status": "ignored"}

        # ---------------- GPT ----------------
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional German language tutor. "
                        "Explain grammar clearly, adapt to user language, and give exercises."
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        answer = response.choices[0].message.content

        # ---------------- SEND BACK TO WHATSAPP ----------------
        send_whatsapp_message(chat_id, answer)

        return {"status": "ok"}

    except Exception as e:
        logger.exception("Error in webhook")
        return {"status": "error", "detail": str(e)}
