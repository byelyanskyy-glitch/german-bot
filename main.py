import os
import logging
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="WhatsApp AI Tutor")

# ─── Config (вшито напрямую) ──────────────────────────────────────────────────
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
GREEN_API_ID    = "7107660125"
GREEN_API_TOKEN = "18af37c556694f5690817d49d289b5134c140fa3d9ad49c49b"
GREEN_API_URL   = "https://7107.api.greenapi.com"

openai_client = OpenAI(api_key=OPENAI_API_KEY)
log.info("OpenAI client initialized")

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — персональный AI-преподаватель немецкого языка.
Определяй язык пользователя автоматически и отвечай на том же языке.
Объясняй грамматику, создавай упражнения и тесты, веди диалог как живой учитель.
Отвечай коротко и по делу — это мессенджер, не книга.
""".strip()

# ─── Helper: отправка сообщения через Green-API ───────────────────────────────
async def send_whatsapp(chat_id: str, text: str) -> bool:
    url = f"{GREEN_API_URL}/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {"chatId": chat_id, "message": text}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            log.info(f"[SEND] ✅ Sent to {chat_id} | status={r.status_code}")
            return True
    except Exception as e:
        log.error(f"[SEND] ❌ Failed to send to {chat_id}: {e}")
        return False

# ─── Helper: вызов GPT ────────────────────────────────────────────────────────
def call_gpt(user_text: str) -> str:
    log.info(f"[GPT] Calling GPT-4o: {user_text[:80]!r}")
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_text},
        ],
        max_tokens=600,
        temperature=0.7,
    )
    answer = response.choices[0].message.content.strip()
    log.info(f"[GPT] ✅ Response: {len(answer)} chars")
    return answer

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    event_type = body.get("typeWebhook", "")
    log.info(f"[WEBHOOK] Event: {event_type}")

    # Обрабатываем только входящие сообщения от пользователя
    if event_type != "incomingMessageReceived":
        return JSONResponse({"status": "skipped", "reason": event_type})

    sender_data  = body.get("senderData", {})
    chat_id      = sender_data.get("chatId", "")

    message_data = body.get("messageData", {})
    msg_type     = message_data.get("typeMessage", "")

    if msg_type != "textMessage":
        log.info(f"[WEBHOOK] Skipped non-text: {msg_type}")
        return JSONResponse({"status": "skipped", "reason": msg_type})

    user_text = message_data.get("textMessageData", {}).get("textMessage", "").strip()

    if not chat_id or not user_text:
        log.warning(f"[WEBHOOK] Empty chat_id or text")
        return JSONResponse({"status": "skipped", "reason": "empty"})

    log.info(f"[WEBHOOK] ✅ From {chat_id}: {user_text[:80]!r}")

    # GPT
    try:
        gpt_answer = call_gpt(user_text)
    except Exception as e:
        log.error(f"[GPT] ❌ {e}")
        await send_whatsapp(chat_id, "⚠️ Ошибка AI. Попробуй ещё раз.")
        raise HTTPException(status_code=500, detail="GPT error")

    # Отправка
    sent = await send_whatsapp(chat_id, gpt_answer)
    if not sent:
        raise HTTPException(status_code=502, detail="Send failed")

    return JSONResponse({"status": "ok"})

# ─── Health check (HEAD + GET) ────────────────────────────────────────────────
@app.get("/")
@app.head("/")
def health():
    return {"status": "alive"}
