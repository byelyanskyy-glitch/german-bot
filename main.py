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

GREEN_API_INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID")
GREEN_API_TOKEN = os.getenv("GREEN_API_TOKEN")
GREEN_API_URL = "https://api.green-api.com"

# ---------------- OPENAI ----------------
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is missing in Render environment variables")

client = OpenAI(api_key=OPENAI_API_KEY or "dummy_key")

# ---------------- HEALTH ----------------
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"ok": True}

# ---------------- GREEN-API SEND MESSAGE ----------------
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
        logger.exception(f"Failed to send message: {e}")
        return None

# ---------------- WEBHOOK ----------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Incoming webhook: {data}")

        message_data = data.get("messageData", {})
        text = message_data.get("textMessageData", {}).get("textMessage")

        sender = data.get("senderData", {})
        chat_id = sender.get("chatId")

        if not text or not chat_id:
            return {"status": "ignored"}

        # ---------------- GPT CALL ----------------
        if OPENAI_API_KEY:
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
        else:
            answer = "OpenAI key is missing. Please configure environment variables."

        # ---------------- SEND RESPONSE ----------------
        send_whatsapp_message(chat_id, answer)

        return {"status": "ok"}

    except Exception as e:
        logger.exception("Webhook error")
        return {"status": "error", "detail": str(e)}
