import os
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="German AI Tutor Bot")

# ─── Config ───────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY    = os.environ.get("OPENROUTER_API_KEY", "")
GREEN_API_INSTANCE_ID = "7107660125"
GREEN_API_TOKEN       = "18af37c556694f5690817d49d289b5134c140fa3d9ad49c49b"
GREEN_API_BASE        = "https://7107.api.greenapi.com"

if not OPENROUTER_API_KEY:
    log.error("❌ OPENROUTER_API_KEY is missing!")
else:
    log.info("✅ OPENROUTER_API_KEY loaded")

# ─── OpenRouter client ────────────────────────────────────────────────────────
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)
log.info("✅ OpenRouter client initialized")

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — профессиональный преподаватель немецкого языка.
Определяй язык пользователя автоматически и отвечай на том же языке.
Объясняй грамматику просто, давай упражнения и примеры.
Отвечай кратко — это WhatsApp, не учебник.
""".strip()

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/")
@app.head("/")
def root():
    return {"status": "ok"}

# ─── Send WhatsApp message ────────────────────────────────────────────────────
async def send_whatsapp(chat_id: str, text: str) -> bool:
    url = f"{GREEN_API_BASE}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.post(url, json=payload)
        log.info(f"[SEND] ✅ status={r.status_code} to {chat_id}")
        return r.status_code == 200
    except Exception as e:
        log.error(f"[SEND] ❌ {e}")
        return False

# ─── Call AI ──────────────────────────────────────────────────────────────────
def call_ai(text: str) -> str:
    log.info(f"[AI] Calling with: {text[:80]!r}")
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ],
        temperature=0.7,
        max_tokens=500,
    )
    answer = response.choices[0].message.content.strip()
    log.info(f"[AI] ✅ Response: {len(answer)} chars")
    return answer

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    event_type = body.get("typeWebhook", "")
    log.info(f"[WEBHOOK] Event: {event_type}")

    # Пропускаем всё кроме входящих сообщений
    if event_type != "incomingMessageReceived":
        log.info(f"[WEBHOOK] Skipped: {event_type}")
        return JSONResponse({"status": "ignored"})

    # Извлекаем данные
    chat_id   = body.get("senderData", {}).get("chatId", "")
    user_text = body.get("messageData", {}).get("textMessageData", {}).get("textMessage", "").strip()

    log.info(f"[WEBHOOK] chat_id={chat_id!r} text={user_text[:80]!r}")

    if not chat_id or not user_text:
        log.warning("[WEBHOOK] Empty chat_id or text — skipping")
        return JSONResponse({"status": "empty"})

    # Вызов AI
    try:
        answer = call_ai(user_text)
    except Exception as e:
        log.error(f"[AI] ❌ {e}")
        await send_whatsapp(chat_id, "⚠️ Ошибка AI, попробуй позже")
        return JSONResponse({"status": "ai_error"})

    # Отправка ответа
    await send_whatsapp(chat_id, answer)
    return JSONResponse({"status": "ok"})
