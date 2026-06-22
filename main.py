import os
import logging
import httpx
from fastapi import FastAPI, Request, HTTPException
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
app = FastAPI(title="WhatsApp AI German Tutor")

# ─────────────────────────────────────────────
# ENV (Render Variables)
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

GREEN_API_ID = os.environ.get("GREEN_API_INSTANCE_ID", "")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN", "")
GREEN_API_URL = "https://7107.api.greenapi.com"

# ─────────────────────────────────────────────
# OPENROUTER CLIENT
# ─────────────────────────────────────────────
if not OPENROUTER_API_KEY:
    log.error("OPENROUTER_API_KEY is missing!")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

log.info("OpenRouter client initialized")

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — персональный AI-преподаватель немецкого языка.
Ты:
- объясняешь грамматику просто
- даёшь примеры
- создаёшь упражнения
- адаптируешься под уровень ученика
- отвечаешь кратко (это WhatsApp)
""".strip()

# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.get("/")
@app.head("/")
def health():
    return {"status": "alive"}

# ─────────────────────────────────────────────
# SEND MESSAGE (Green-API)
# ─────────────────────────────────────────────
async def send_whatsapp(chat_id: str, text: str):
    if not GREEN_API_ID or not GREEN_API_TOKEN:
        log.error("Green-API credentials missing")
        return False

    url = f"{GREEN_API_URL}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"

    payload = {
        "chatId": chat_id,
        "message": text
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client_http:
            r = await client_http.post(url, json=payload)
            log.info(f"[SEND] status={r.status_code} chat={chat_id}")
            return True
    except Exception as e:
        log.error(f"[SEND ERROR] {e}")
        return False

# ─────────────────────────────────────────────
# GPT CALL (OpenRouter)
# ─────────────────────────────────────────────
def call_ai(text: str) -> str:
    log.info(f"[AI] Request: {text[:80]!r}")

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3-0324:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.7,
        max_tokens=600,
    )

    answer = response.choices[0].message.content.strip()

    log.info(f"[AI] Response length: {len(answer)}")

    return answer

# ─────────────────────────────────────────────
# WEBHOOK
# ─────────────────────────────────────────────
log.info(f"[RAW WEBHOOK] {body}")
@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
        log.info(f"[WEBHOOK] Event: {body.get('typeWebhook')}")

        event_type = body.get("typeWebhook")

        # ─────────────────────────────
        # FILTER EVENTS
        # ─────────────────────────────
        if event_type != "incomingMessageReceived":
            return {"status": "ignored", "event": event_type}

        sender_data = body.get("senderData", {})
        chat_id = sender_data.get("chatId", "")

        message_data = body.get("messageData", {})
        msg_type = message_data.get("typeMessage", "")

        # ─────────────────────────────
        # PARSE TEXT (IMPORTANT FIX)
        # ─────────────────────────────
        if msg_type == "textMessage":
            user_text = (
                message_data
                .get("textMessageData", {})
                .get("textMessage", "")
                .strip()
            )

        elif msg_type == "extendedTextMessage":
            user_text = (
                message_data
                .get("extendedTextMessageData", {})
                .get("text", "")
                .strip()
            )

        else:
            log.info(f"[WEBHOOK] Skipped type: {msg_type}")
            return {"status": "skipped"}

        if not chat_id or not user_text:
            return {"status": "empty"}

        log.info(f"[USER] {chat_id}: {user_text}")

        # ─────────────────────────────
        # AI RESPONSE
        # ─────────────────────────────
        try:
            answer = call_ai(user_text)
        except Exception as e:
            log.error(f"[AI ERROR] {e}")
            answer = "⚠️ Ошибка AI. Попробуй ещё раз."

        # ─────────────────────────────
        # SEND BACK
        # ─────────────────────────────
        ok = await send_whatsapp(chat_id, answer)

        if not ok:
            raise HTTPException(status_code=500, detail="Send failed")

        return {"status": "ok"}

    except Exception as e:
        log.exception("Webhook crashed")
        return JSONResponse({"status": "error", "detail": str(e)})
