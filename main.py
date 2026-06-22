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

# ─── Config ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY   = os.environ["OPENAI_API_KEY"]
GREEN_API_ID     = os.environ["GREEN_API_ID"]       # e.g. "7107XXXXXX"
GREEN_API_TOKEN  = os.environ["GREEN_API_TOKEN"]    # instanceToken

openai_client = OpenAI(api_key=OPENAI_API_KEY)

GREEN_API_BASE = f"https://api.green-api.com/waInstance{GREEN_API_ID}"

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Ты — персональный AI-преподаватель немецкого языка.
Определяй язык пользователя автоматически и отвечай на том же языке.
Объясняй грамматику, создавай упражнения и тесты, веди диалог как живой учитель.
Отвечай коротко и по делу — это мессенджер, не книга.
""".strip()

# ─── Helper: send message via Green-API ───────────────────────────────────────
async def send_whatsapp(chat_id: str, text: str) -> bool:
    url = f"{GREEN_API_BASE}/sendMessage/{GREEN_API_TOKEN}"
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

# ─── Helper: call GPT ─────────────────────────────────────────────────────────
def call_gpt(user_text: str) -> str:
    log.info(f"[GPT] Calling GPT-4o with: {user_text[:80]!r}")
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
    log.info(f"[GPT] ✅ Response received ({len(answer)} chars)")
    return answer

# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    event_type = body.get("typeWebhook", "")
    log.info(f"[WEBHOOK] Received event: {event_type}")
    log.debug(f"[WEBHOOK] Full payload: {body}")

    # ── 1. Фильтр: нас интересуют ТОЛЬКО входящие сообщения ──────────────────
    #    Green-API посылает разные типы:
    #      incomingMessageReceived  — сообщение ОТ пользователя  ✅ нужно
    #      outgoingMessageReceived  — статус НАШЕГО исходящего   ❌ пропускаем
    #      outgoingAPIMessageReceived — то же, через API         ❌ пропускаем
    #      stateInstanceChanged, deviceInfo, statusInstanceChanged — служебные ❌

    INCOMING_EVENTS = {"incomingMessageReceived"}

    if event_type not in INCOMING_EVENTS:
        log.info(f"[WEBHOOK] Skipped non-incoming event: {event_type}")
        return JSONResponse({"status": "skipped", "reason": event_type})

    # ── 2. Извлекаем chat_id и текст ─────────────────────────────────────────
    sender_data = body.get("senderData", {})
    chat_id     = sender_data.get("chatId", "")

    message_data = body.get("messageData", {})
    msg_type     = message_data.get("typeMessage", "")

    # Поддерживаем только текстовые сообщения
    if msg_type != "textMessage":
        log.info(f"[WEBHOOK] Skipped non-text message type: {msg_type}")
        return JSONResponse({"status": "skipped", "reason": f"type={msg_type}"})

    text_message = message_data.get("textMessageData", {})
    user_text    = text_message.get("textMessage", "").strip()

    if not chat_id or not user_text:
        log.warning(f"[WEBHOOK] Empty chat_id or text — payload: {body}")
        return JSONResponse({"status": "skipped", "reason": "empty"})

    log.info(f"[WEBHOOK] ✅ Message from {chat_id}: {user_text[:80]!r}")

    # ── 3. GPT ────────────────────────────────────────────────────────────────
    try:
        gpt_answer = call_gpt(user_text)
    except Exception as e:
        log.error(f"[GPT] ❌ Error: {e}")
        await send_whatsapp(chat_id, "⚠️ Произошла ошибка. Попробуй ещё раз.")
        raise HTTPException(status_code=500, detail="GPT error")

    # ── 4. Отправляем ответ ───────────────────────────────────────────────────
    sent = await send_whatsapp(chat_id, gpt_answer)
    if not sent:
        raise HTTPException(status_code=502, detail="Failed to send WhatsApp message")

    return JSONResponse({"status": "ok", "chat_id": chat_id})

# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "alive"}
