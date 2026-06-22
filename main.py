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

# ---------------- ENV VARIABLES ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")
GREEN_API_URL = "https://api.green-api.com"

# ---------------- OPENAI CLIENT ----------------
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None
    logger.error("OPENAI_API_KEY is missing in Render environment variables")

# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"ok": True}

# ---------------- SEND MESSAGE ----------------
def send_whatsapp_message(chat_id: str, text: str):
    if not GREEN_API_INSTANCE_ID or not GREEN_API_TOKEN:
        logger.error("Green-API credentials missing")
        return None

    url = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"

    payload = {
        "chatId": chat_id,
        "message": text
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        logger.info(f"Green-API response: {response.status_code} {response.text}")
        return response.json()
    except Exception as e:
        logger.exception(f"Error sending WhatsApp message: {e}")
        return None

# ---------------- WEBHOOK ----------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Incoming webhook: {data}")

        # ❗ фильтр — только входящие сообщения пользователя
        if data.get("typeWebhook") != "incomingMessageReceived":
            return {"status": "ignored"}

        message_data = data.get("messageData", {})
        text = message_data.get("textMessageData", {}).get("textMessage")

        sender = data.get("senderData", {})
        chat_id = sender.get("chatId")

        if not text or not chat_id:
            return {"status": "ignored"}

        # ---------------- GPT ----------------
        if client:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional German language tutor. "
                            "Explain grammar clearly, adapt to user's language, "
                            "and give exercises and corrections."
                        )
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            )

            answer = response.choices[0].message.content
        else:
            answer = "OpenAI API key is missing. Please set environment variables in Render."

        # ---------------- SEND RESPONSE ----------------
        send_whatsapp_message(chat_id, answer)

        return {"status": "ok"}

    except Exception as e:
        logger.exception("Webhook error")
        return {"status": "error", "detail": str(e)}
