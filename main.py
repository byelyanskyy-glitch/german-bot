import os
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────
app = FastAPI(title="German AI Tutor Bot")

# ─────────────────────────────────────────────
# ENV (Render Environment Variables)
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

GREEN_API_INSTANCE_ID = os.environ.get("GREEN_API_INSTANCE_ID", "")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "")
GREEN_API_BASE = "https://7107.api.greenapi.com"

if not OPENROUTER_API_KEY:
    log.error("OPENROUTER_API_KEY is missing!")

# ─────────────────────────────────────────────
# OpenRouter client
# ─────────────────────────────────────────────
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

log.info("OpenRouter client initialized")

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — профессиональный преподаватель немецкого языка.
Определи язык пользователя автоматически.
Отвечай кратко, как в WhatsApp.
Давай упражнения и объясняй грамматику просто.
""".strip()

# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.get("/")
@app.head("/")
def root():
    return {"status": "ok"}

# ─────────────────────────────────────────────
# SEND MESSAGE TO WHATSAPP
# ─────────────────────────────────────────────
async def send_whatsapp(chat_id: str, text: str):
    url = f"{GREEN_API_BASE}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"

    payload = {
        "chatId": chat_id,
        "message": text
    }

    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(url, json=payload)

    log.info(f"[SEND] status={r.status_code}")
    return r.status_code == 200

# ─────────────────────────────────────────────
# GPT / OPENROUTER CALL
# ─────────────────────────────────────────────
def call_ai(text: str) -> str:
    log.info(f"[AI] {text[:80]}")

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        temperature=0.7,
        max_tokens=500
    )

    return response.choices[0].message.content.strip()

# ─────────────────────────────────────────────
# WEBHOOK
# ─────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    log.info(f"[WEBHOOK] {body}")

    event_type = body.get("typeWebhook", "")

    # фильтр только входящих сообщений
    if event_type != "incomingMessageReceived":
        return JSONResponse({"status": "ignored"})

    sender = body.get("senderData", {})
    chat_id = sender.get("chatId")

    message = body.get("messageData", {})
    text = message.get("textMessageData", {}).get("textMessage", "")

    if not chat_id or not text:
        return JSONResponse({"status": "empty"})

    try:
        answer = call_ai(text)
    except Exception as e:
        log.exception("AI error")
        await send_whatsapp(chat_id, "Ошибка AI, попробуй позже")
        return JSONResponse({"status": "ai_error"})

    await send_whatsapp(chat_id, answer)

    return JSONResponse({"status": "ok"})
