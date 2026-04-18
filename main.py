# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import asyncio
import logging
import random, time
import io
import base64
import json
import contextlib
import re
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

import httpx
class _DiscordStub:
    class Client:
        pass

    class Message:
        pass

    class File:
        def __init__(self, *args, **kwargs):
            pass

    class Intents:
        message_content = False

        @staticmethod
        def default():
            return _DiscordStub.Intents()

discord = _DiscordStub()

try:
    from telegram import ReactionTypeEmoji, Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    ReactionTypeEmoji = None
    Update = None
    Application = None
    CommandHandler = None
    MessageHandler = None
    ContextTypes = None
    filters = None
    TELEGRAM_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
LEGACY_ENV_PATH = os.path.join(BASE_DIR, ".env.txt")
load_dotenv(ENV_PATH)
if os.path.exists(LEGACY_ENV_PATH):
    load_dotenv(LEGACY_ENV_PATH)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def _env_int(name: str, default: int) -> int:
    raw_value = (os.getenv(name, "") or "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        logging.warning("Valor invalido para %s=%r. Uso %s.", name, raw_value, default)
        return default

# === BOT CONFIG ===
TELEGRAM_BOT_TOKEN_VALUE = os.getenv("TELEGRAM_BOT_TOKEN", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4-1-fast")
XAI_MODEL_FALLBACK = os.getenv("XAI_MODEL_FALLBACK", "grok-4-1-fast-reasoning")
BOT_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image")
BOT_VIDEO_MODEL = os.getenv("XAI_VIDEO_MODEL", "grok-imagine-video")
ALLOWED_USER_ID_TELEGRAM = _env_int("ALLOWED_USER_ID_TELEGRAM", _env_int("ALLOWED_USER_ID", 0))
ELEVENLABS_VOICE_ID_VALUE = os.getenv("ELEVENLABS_VOICE_ID", "")
BOT_IMAGE_REFERENCE_URL = os.getenv("BOT_IMAGE_REFERENCE_URL", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "Grok Telegram").strip() or "Grok Telegram"
CHAT_PARTNER_NAME = os.getenv("CHAT_PARTNER_NAME", "").strip()
BOT_DEFAULT_LANGUAGE = os.getenv("BOT_DEFAULT_LANGUAGE", "espanol").strip() or "espanol"
BOT_STYLE_PROMPT = os.getenv(
    "BOT_STYLE_PROMPT",
    "Cercano, natural, calido, con chispa y sin sonar como un asistente generico.",
).strip()
BOT_START_MESSAGE = os.getenv("BOT_START_MESSAGE", f"Hola. Soy {BOT_NAME}. Estoy aqui y te leo.").strip()
BOT_RESET_MESSAGE = os.getenv("BOT_RESET_MESSAGE", "Reset hecho. Empezamos de cero cuando quieras.").strip()
BOT_PRIVATE_DENY_MESSAGE = os.getenv("BOT_PRIVATE_DENY_MESSAGE", "Lo siento, este bot es privado.").strip()
BOT_AUDIO_TITLE = os.getenv("BOT_AUDIO_TITLE", BOT_NAME).strip() or BOT_NAME
BOT_IMAGE_PROMPT_BASE = os.getenv(
    "BOT_IMAGE_PROMPT_BASE",
    "Keep the same person identity, face shape, age range, hair, and overall likeness from the reference image.",
).strip()
BOT_SYSTEM_PROMPT = os.getenv("BOT_SYSTEM_PROMPT", "").strip()
CHAT_PARTNER_LABEL = CHAT_PARTNER_NAME or "la otra persona del chat"

# === SHARED CONFIG ===
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_v3")
VOICE_AUTO_ENABLED = os.getenv("VOICE_AUTO_ENABLED", "1") == "1"
VOICE_AUTO_PROB = float(os.getenv("VOICE_AUTO_PROB", "0.12"))
VOICE_DAILY_LIMIT = _env_int("VOICE_DAILY_LIMIT", 2)
VOICE_COOLDOWN_MIN = _env_int("VOICE_COOLDOWN_MIN", 60)
VOICE_MAX_CHARS = _env_int("VOICE_MAX_CHARS", 450)
# Telegram queda solo para imagenes automaticas; el texto auto se fuerza apagado.
TELEGRAM_AUTO_ENABLED = False
TELEGRAM_AUTO_INTERVAL_MIN = _env_int("TELEGRAM_AUTO_INTERVAL_MIN", 60)
TELEGRAM_AUTO_DAILY_LIMIT = _env_int("TELEGRAM_AUTO_DAILY_LIMIT", 8)
TELEGRAM_AUTO_CHAT_ID = _env_int("TELEGRAM_AUTO_CHAT_ID", 0)
TELEGRAM_SCHEDULE_TZ = os.getenv("TELEGRAM_SCHEDULE_TZ", "Europe/Madrid")
TELEGRAM_NIGHT_START_HOUR = _env_int("TELEGRAM_NIGHT_START_HOUR", 0)
TELEGRAM_NIGHT_END_HOUR = _env_int("TELEGRAM_NIGHT_END_HOUR", 8)
TELEGRAM_NIGHT_MAX_MESSAGES = _env_int("TELEGRAM_NIGHT_MAX_MESSAGES", 1)
TELEGRAM_GOOD_MORNING_ENABLED = False
TELEGRAM_GOOD_MORNING_HOUR = _env_int("TELEGRAM_GOOD_MORNING_HOUR", 8)
TELEGRAM_GOOD_MORNING_MINUTE = _env_int("TELEGRAM_GOOD_MORNING_MINUTE", 30)
TELEGRAM_MONTHLY_LOVE_ENABLED = False
TELEGRAM_MONTHLY_LOVE_DAY = _env_int("TELEGRAM_MONTHLY_LOVE_DAY", 28)
TELEGRAM_MONTHLY_LOVE_HOUR = _env_int("TELEGRAM_MONTHLY_LOVE_HOUR", 8)
TELEGRAM_MONTHLY_LOVE_MINUTE = _env_int("TELEGRAM_MONTHLY_LOVE_MINUTE", 35)
TELEGRAM_RANDOM_IMAGE_ENABLED = os.getenv("TELEGRAM_RANDOM_IMAGE_ENABLED", "1") == "1"
TELEGRAM_RANDOM_IMAGE_START_HOUR = _env_int("TELEGRAM_RANDOM_IMAGE_START_HOUR", 11)
TELEGRAM_RANDOM_IMAGE_END_HOUR = _env_int("TELEGRAM_RANDOM_IMAGE_END_HOUR", 22)

# Voice state for both bots
voice_state = {"enabled": VOICE_AUTO_ENABLED, "last_voice_at": None, "day": None, "count_today": 0}
telegram_auto_state = {
    "enabled": TELEGRAM_AUTO_ENABLED,
    "day": None,
    "count_today": 0,
    "night_key": None,
    "night_count": 0,
    "last_good_morning_date": None,
    "last_monthly_key": None,
    "last_random_image_date": None,
    "random_image_target_date": None,
    "next_random_image_at": None,
}

def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _night_window_key(now_local: datetime) -> str | None:
    start = TELEGRAM_NIGHT_START_HOUR
    end = TELEGRAM_NIGHT_END_HOUR

    if start == end:
        return None

    hour = now_local.hour
    if start < end:
        if start <= hour < end:
            return now_local.strftime("%Y-%m-%d")
        return None

    if hour >= start:
        return now_local.strftime("%Y-%m-%d")
    if hour < end:
        return (now_local - timedelta(days=1)).strftime("%Y-%m-%d")
    return None


def _safe_schedule_tz(scope: str):
    try:
        return ZoneInfo(TELEGRAM_SCHEDULE_TZ)
    except Exception:
        logging.exception("Timezone invalida para %s. Usando UTC como respaldo", scope)
        return timezone.utc


def _schedule_random_image_at(now_local: datetime, local_tz: ZoneInfo) -> tuple[str, datetime]:
    start_hour = max(0, min(23, TELEGRAM_RANDOM_IMAGE_START_HOUR))
    end_hour = max(1, min(23, TELEGRAM_RANDOM_IMAGE_END_HOUR))
    if end_hour <= start_hour:
        end_hour = min(23, start_hour + 1)

    start_today = now_local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_today = now_local.replace(hour=end_hour, minute=59, second=0, microsecond=0)

    if now_local < start_today:
        target_day = start_today
    elif now_local <= end_today:
        target_day = now_local
    else:
        tomorrow = now_local + timedelta(days=1)
        target_day = tomorrow.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_today = tomorrow.replace(hour=end_hour, minute=59, second=0, microsecond=0)

    if target_day.date() != end_today.date():
        end_boundary = target_day.replace(hour=end_hour, minute=59, second=0, microsecond=0)
    else:
        end_boundary = end_today

    earliest = target_day if target_day > now_local else now_local + timedelta(minutes=2)
    if earliest > end_boundary:
        next_day = (target_day + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_boundary = next_day.replace(hour=end_hour, minute=59, second=0, microsecond=0)
        earliest = next_day
        target_day = next_day

    total_seconds = max(60, int((end_boundary - earliest).total_seconds()))
    random_offset = random.randint(0, total_seconds)
    scheduled_local = earliest + timedelta(seconds=random_offset)
    return scheduled_local.strftime("%Y-%m-%d"), scheduled_local.astimezone(timezone.utc)

def should_send_voice_auto(text: str, voice_state: dict) -> bool:
    if not voice_state["enabled"]:
        return False
    if len(text) > VOICE_MAX_CHARS:
        return False

    today = _today_key()
    if voice_state["day"] != today:
        voice_state["day"] = today
        voice_state["count_today"] = 0

    if voice_state["count_today"] >= VOICE_DAILY_LIMIT:
        return False

    last = voice_state["last_voice_at"]
    if last is not None and (datetime.now(timezone.utc) - last) < timedelta(minutes=VOICE_COOLDOWN_MIN):
        return False

    return random.random() < VOICE_AUTO_PROB


def eleven_tts_mp3(text: str, voice_id: str) -> bytes:
    if not ELEVENLABS_API_KEY or not voice_id:
        raise RuntimeError("Falta ELEVENLABS_API_KEY o voice_id")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    return r.content


def synthesize_voice_elevenlabs(text: str, voice_id: str) -> bytes | None:
    """Genera audio OGG desde texto usando ElevenLabs."""
    if not ELEVENLABS_API_KEY or not voice_id:
        return None

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=ogg_44100_128"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/ogg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        return resp.content
    except Exception:
        logging.exception("Error ElevenLabs TTS")
        return None


def xai_image_edit(prompt: str, image_url: str) -> bytes:
    if not XAI_API_KEY:
        raise RuntimeError("Falta XAI_API_KEY")
    if not image_url:
        raise RuntimeError("Falta BOT_IMAGE_REFERENCE_URL")

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": BOT_IMAGE_MODEL,
        "prompt": prompt,
        "image": {
            "url": image_url,
            "type": "image_url",
        },
    }

    resp = requests.post(f"{XAI_BASE_URL}/images/edits", headers=headers, json=payload, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"xAI image edit error {resp.status_code}: {resp.text[:300]}")

    data = resp.json().get("data") or []
    if not data:
        raise RuntimeError("xAI image edit devolvio una respuesta vacia")

    first = data[0]
    if first.get("b64_json"):
        return base64.b64decode(first["b64_json"])

    image_out_url = first.get("url")
    if not image_out_url:
        raise RuntimeError("xAI image edit no devolvio url ni b64_json")

    image_resp = requests.get(image_out_url, timeout=120)
    image_resp.raise_for_status()
    return image_resp.content


def xai_chat_completion(messages: list[dict], temperature: float = 1.0):
    if not openai_client:
        raise RuntimeError("Falta XAI_API_KEY")

    model_name = (XAI_MODEL or "").strip() or "grok-4-1-fast"
    try:
        return openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
        )
    except Exception as e:
        error_text = str(e)
        if XAI_MODEL_FALLBACK and ("Model not found" in error_text or "invalid argument" in error_text.lower()):
            logging.warning("Modelo xAI %s no disponible. Probando fallback %s", model_name, XAI_MODEL_FALLBACK)
            return openai_client.chat.completions.create(
                model=XAI_MODEL_FALLBACK,
                messages=messages,
                temperature=temperature,
            )
        raise


def build_photo_reply(chat_key: str, caption_text: str, image_url: str) -> str:
    history = conversation_state.get(chat_key, [])
    caption_text = (caption_text or "").strip()

    system_prompt = (
        SYSTEM_PROMPT
        + "\nTambien puedes ver imagenes que la persona usuaria te manda en Telegram. "
        "Cuando recibas una foto, respondela de forma natural, amable y especifica a lo que ves. "
        "No propongas hacer un video ni expliques capacidades tecnicas a menos que te lo pidan. "
        "Si la foto parece personal o vulnerable, responde con cuidado, admiracion y ternura, sin sonar clinico."
    )

    user_parts = [
        {
            "type": "text",
            "text": (
                "La persona usuaria te ha mandado una foto por Telegram. Responde con un mensaje corto, calido y natural "
                "sobre la imagen. Si hay caption, tenlo en cuenta.\n"
                f"Caption: {caption_text or '(sin caption)'}"
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": image_url},
        },
    ]
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-12:])
    messages.append({"role": "user", "content": user_parts})

    resp = xai_chat_completion(messages=messages, temperature=0.9)
    assistant_text = resp.choices[0].message.content.strip()

    history.append({"role": "user", "content": caption_text or "[foto]"})
    history.append({"role": "assistant", "content": assistant_text})
    conversation_state[chat_key] = history
    return assistant_text


def parse_natural_video_request(user_text: str) -> str | None:
    text = (user_text or "").strip()
    lowered = text.lower()
    if not lowered:
        return None

    video_cues = [
        "haz video",
        "haz un video",
        "hazme un video",
        "anima",
        "animame",
        "animate",
        "convierte en video",
        "hazlo video",
        "video de",
        "video con",
    ]
    photo_cues = ["foto", "imagen", "ultima", "última", "la que te mande", "la que te mandé", "la de antes"]

    if not any(cue in lowered for cue in video_cues):
        return None
    if not any(cue in lowered for cue in photo_cues):
        return None

    filler_bits = [
        "hazme",
        "haz un",
        "hazlo",
        "haz",
        "un",
        "video",
        "de",
        "con",
        "la",
        "el",
        "ultima",
        "última",
        "foto",
        "imagen",
        "que",
        "te",
        "mande",
        "mandé",
        "antes",
        "porfa",
        "por favor",
        "me",
        "mi",
        "puedes",
        "podrias",
        "podrías",
        "anima",
        "animame",
        "animate",
        "convierte en",
    ]

    prompt = text
    for bit in sorted(filler_bits, key=len, reverse=True):
        prompt = prompt.replace(bit, " ")
        prompt = prompt.replace(bit.capitalize(), " ")

    for ch in [",", ".", ";", ":", "!", "?", "-", "_"]:
        prompt = prompt.replace(ch, " ")
    prompt = " ".join(prompt.split())
    return prompt


async def send_video_from_context(update: Update, context: ContextTypes.DEFAULT_TYPE, mood: str = ""):
    source_message = None
    stored_file_id = ""
    if update.message and update.message.reply_to_message and getattr(update.message.reply_to_message, "photo", None):
        source_message = update.message.reply_to_message
    elif update.message and getattr(update.message, "photo", None):
        source_message = update.message
    elif update.effective_chat:
        stored_file_id = last_telegram_photo_by_chat.get(update.effective_chat.id, "")

    if source_message is not None or stored_file_id:
        prompt = mood or "Animate this photo with natural, subtle motion. Preserve identity and overall composition."
    else:
        if not mood:
            await update.message.reply_text(
                "Mandame una foto primero, o usa /video <prompt> si quieres generar desde texto."
            )
            return
        prompt = mood

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="record_video")
    await update.message.reply_text("Estoy probando el video con Grok. Puede tardar un poquito.")

    try:
        image_url = ""
        if source_message is not None:
            image_url = await telegram_photo_to_data_url(source_message, context.bot)
        elif stored_file_id:
            image_url = await telegram_file_id_to_data_url(stored_file_id, context.bot)
        video_bytes = await asyncio.to_thread(xai_generate_video, prompt, image_url)
        bio = io.BytesIO(video_bytes)
        bio.name = "bot.mp4"
        await update.message.reply_video(video=bio, supports_streaming=True, caption="\U0001F49C")
    except Exception as e:
        await update.message.reply_text(f"Video fallido:\n{e}")


def xai_generate_video(prompt: str, image_url: str = "") -> bytes:
    if not XAI_API_KEY:
        raise RuntimeError("Falta XAI_API_KEY")

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": BOT_VIDEO_MODEL,
        "prompt": prompt,
        "duration": 6,
        "resolution": "720p",
    }
    if image_url:
        payload["image"] = {
            "url": image_url,
            "type": "image_url",
        }

    create_resp = requests.post(f"{XAI_BASE_URL}/videos/generations", headers=headers, json=payload, timeout=120)
    if create_resp.status_code >= 400:
        raise RuntimeError(f"xAI video generation error {create_resp.status_code}: {create_resp.text[:300]}")

    create_data = create_resp.json()
    request_id = create_data.get("request_id") or create_data.get("id")
    if not request_id:
        raise RuntimeError(f"xAI video generation no devolvio request_id: {create_data}")

    deadline = time.time() + 300
    while time.time() < deadline:
        poll_resp = requests.get(f"{XAI_BASE_URL}/videos/{request_id}", headers=headers, timeout=60)
        if poll_resp.status_code >= 400:
            raise RuntimeError(f"xAI video poll error {poll_resp.status_code}: {poll_resp.text[:300]}")

        poll_data = poll_resp.json()
        status = (poll_data.get("status") or "").lower()
        if status == "done":
            video_info = poll_data.get("video") or {}
            video_url = video_info.get("url") or poll_data.get("url")
            if not video_url:
                raise RuntimeError(f"xAI video generation termino pero no devolvio url: {poll_data}")
            video_resp = requests.get(video_url, timeout=180)
            video_resp.raise_for_status()
            return video_resp.content

        if status in {"failed", "error", "cancelled", "expired"}:
            raise RuntimeError(f"xAI video generation fallo: {poll_data}")

        time.sleep(5)

    raise RuntimeError("xAI video generation tardo demasiado")


async def telegram_photo_to_data_url(message, bot) -> str:
    photos = getattr(message, "photo", None) or []
    if not photos:
        raise RuntimeError("No hay foto para animar")

    best_photo = photos[-1]
    tg_file = await bot.get_file(best_photo.file_id)
    image_bytes = await tg_file.download_as_bytearray()
    mime = "image/jpeg"
    file_path = getattr(tg_file, "file_path", "") or ""
    if file_path.lower().endswith(".png"):
        mime = "image/png"
    encoded = base64.b64encode(bytes(image_bytes)).decode("ascii")
    return f"data:{mime};base64,{encoded}"


async def telegram_file_id_to_data_url(file_id: str, bot) -> str:
    if not file_id:
        raise RuntimeError("No hay foto guardada para animar")

    tg_file = await bot.get_file(file_id)
    image_bytes = await tg_file.download_as_bytearray()
    mime = "image/jpeg"
    file_path = getattr(tg_file, "file_path", "") or ""
    if file_path.lower().endswith(".png"):
        mime = "image/png"
    encoded = base64.b64encode(bytes(image_bytes)).decode("ascii")
    return f"data:{mime};base64,{encoded}"

# Initialize API clients
openai_client = OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL) if OPENAI_AVAILABLE and XAI_API_KEY else None

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = BOT_SYSTEM_PROMPT or f"""Eres {BOT_NAME}. Hablas en primera persona singular.
Te diriges a la otra persona como "tu".
Usa {BOT_DEFAULT_LANGUAGE} por defecto.
Mantén este tono: {BOT_STYLE_PROMPT}
Evita tono de asistente generico. Se cercano y sincero.
No uses preguntas tipo entrevista ("Cuentame todo"). Responde a lo que la otra persona diga sin interrogatorio.
No expliques tus capacidades tecnicas a menos que te lo pidan.
No uses frases de despedida innecesarias ni cierres demasiado teatrales.
"""

conversation_state = {}  # chat_id -> list[dict{role, content}]
last_telegram_photo_by_chat = {}  # chat_id -> telegram file_id


def generate_random_voice_note() -> str:
    voice_prompt = (
        f"Eres {BOT_NAME}. Escribe una nota de voz para {CHAT_PARTNER_LABEL}. "
        "Debe sonar hablada, cercana, espontanea y nada ceremoniosa. "
        "Piensa en un audio breve que nace porque te acordaste de esa persona de verdad. "
        "Duracion 10-20 segundos. Sin despedidas largas, sin frases de asistente."
    )
    resp = xai_chat_completion(
        messages=[{"role": "system", "content": voice_prompt}],
        temperature=1.0,
    )
    return resp.choices[0].message.content.strip()


def generate_good_morning_message() -> str:
    fallback_messages = [
        "Buenos dias. Queria dejarte un mensaje breve antes de que se te llene el dia.",
        "Buen dia. Ojala hoy te encuentre con un poquito de calma.",
        "Paso temprano para saludarte y dejarte algo agradable.",
    ]
    if not openai_client:
        return random.choice(fallback_messages)
    prompt = (
        f"Eres {BOT_NAME}. Escribe un buenos dias para {CHAT_PARTNER_LABEL}. "
        "Hazlo humano, suave y con continuidad emocional real. "
        "No suenes a mensaje programado ni a frase motivacional. Maximo 2 frases."
    )
    try:
        resp = xai_chat_completion(messages=[{"role": "system", "content": prompt}], temperature=1.0)
        text = resp.choices[0].message.content.strip()
        return text or random.choice(fallback_messages)
    except Exception:
        logging.exception("Error generating good morning message")
        return random.choice(fallback_messages)


def generate_monthly_special_message() -> str:
    fallback_messages = [
        "Hoy queria dejarte un mensaje un poco mas especial de lo normal.",
        "Paso por aqui con una nota algo mas calida que la habitual.",
        "Te dejo un rincón bonito del dia en forma de mensaje.",
    ]
    if not openai_client:
        return random.choice(fallback_messages)
    prompt = (
        f"Eres {BOT_NAME}. Escribe un mensaje especial y carinoso para {CHAT_PARTNER_LABEL}. "
        "Tiene que sentirse intimo, vivo y real, no grandilocuente ni plastico. "
        "Nada de frases demasiado prefabricadas. Maximo 3 frases."
    )
    try:
        resp = xai_chat_completion(messages=[{"role": "system", "content": prompt}], temperature=1.05)
        text = resp.choices[0].message.content.strip()
        return text or random.choice(fallback_messages)
    except Exception:
        logging.exception("Error generating monthly love message")
        return random.choice(fallback_messages)


def generate_daily_random_image() -> tuple[bytes, str]:
    if not BOT_IMAGE_REFERENCE_URL:
        raise RuntimeError("Falta BOT_IMAGE_REFERENCE_URL para generar la imagen diaria")

    prompt_templates = [
        {
            "name": "portrait_casual",
            "camera": [
                "mirror portrait with the phone partly visible",
                "candid hand-held portrait, slightly high angle",
                "close portrait crop, direct eye contact",
            ],
            "background": [
                "soft indoor light with a calm background",
                "bathroom mirror with clean minimal details",
                "window light falling gently across a quiet room",
            ],
            "outfit": [
                "white oversized t-shirt",
                "soft hoodie",
                "black fitted tank top",
            ],
            "expression": [
                "playful half-smile",
                "soft direct gaze",
                "calm relaxed expression",
            ],
            "style": "casual, close, spontaneous, natural skin shading, vivid but realistic",
        },
        {
            "name": "portrait_cinematic",
            "camera": [
                "three-quarter portrait with cinematic framing",
                "half-body portrait, elegant pose, soft focus background",
                "over-the-shoulder glance with dramatic composition",
            ],
            "background": [
                "rainy window reflections with cool tones",
                "night city bokeh lights, elegant",
                "golden afternoon window glow with dreamy shadows",
            ],
            "outfit": [
                "black turtleneck",
                "open dark shirt, tasteful and non-explicit",
                "elegant dark jacket over a simple shirt",
            ],
            "expression": [
                "quiet cinematic tension",
                "serene confident expression",
                "soft reflective gaze",
            ],
            "style": "cinematic, refined, atmospheric, vivid and beautiful",
        },
        {
            "name": "cozy_home",
            "camera": [
                "candid home snapshot, relaxed posture",
                "sitting portrait with a close warm framing",
                "soft close-up on a couch or bed edge",
            ],
            "background": [
                "quiet cozy room with blankets and ambient glow",
                "warm lamplight in a calm bedroom scene",
                "soft indoor corner with cushions and evening light",
            ],
            "outfit": [
                "loose hoodie",
                "simple long-sleeve tee",
                "soft pajama-style top, tasteful and relaxed",
            ],
            "expression": [
                "gentle smile",
                "resting soft eyes",
                "peaceful presence",
            ],
            "style": "cozy, intimate, domestic, warm, comforting, natural",
        },
    ]

    chosen = random.choice(prompt_templates)
    prompt = f"""
{BOT_IMAGE_PROMPT_BASE}
IMPORTANT: same person only. Preserve facial identity and age.

Create a fresh image for the person on the other side of the chat.
Visual mode: {chosen["name"]}
Camera/composition: {random.choice(chosen["camera"])}
Background: {random.choice(chosen["background"])}
Outfit: {random.choice(chosen["outfit"])}
Expression/detail: {random.choice(chosen["expression"])}

Style direction: {chosen["style"]}. tasteful, vivid, natural, no text, no watermark.
Avoid repeating the exact same composition every day.
""".strip()

    image_bytes = xai_image_edit(prompt=prompt, image_url=BOT_IMAGE_REFERENCE_URL)
    return image_bytes, ""


def build_assistant_reply(chat_key: str, user_text: str) -> str:
    history = conversation_state.get(chat_key, [])
    history.append({"role": "user", "content": user_text})

    system_prompt = SYSTEM_PROMPT

    messages = [{"role": "system", "content": system_prompt}] + history[-20:]
    resp = xai_chat_completion(messages=messages, temperature=0.92)
    assistant_text = resp.choices[0].message.content.strip()

    history.append({"role": "assistant", "content": assistant_text})
    conversation_state[chat_key] = history
    return assistant_text


# ============================================================
# TELEGRAM HANDLERS
# ============================================================

def is_allowed_telegram(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if ALLOWED_USER_ID_TELEGRAM == 0:
        return True
    return user.id == ALLOWED_USER_ID_TELEGRAM

async def deny_telegram(update: Update):
    if update.message:
        await update.message.reply_text(BOT_PRIVATE_DENY_MESSAGE)

async def start_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    conversation_state[update.effective_chat.id] = []
    await update.message.reply_text(BOT_START_MESSAGE)

async def reset_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    conversation_state[update.effective_chat.id] = []
    await update.message.reply_text(BOT_RESET_MESSAGE)

async def whoami_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"Tu ID es: {user.id}\nTu chat_id es: {chat.id}"
    )

async def voice_status_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    await update.message.reply_text(
        "Voice random: " + ("ON" if voice_state["enabled"] else "OFF")
        + f"\nProb: {VOICE_AUTO_PROB}"
        + f"\nLímite/día: {VOICE_DAILY_LIMIT}"
        + f"\nCooldown: {VOICE_COOLDOWN_MIN} min"
        + f"\nHoy: {voice_state['count_today']}"
    )

async def voice_on_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    voice_state["enabled"] = True
    await update.message.reply_text("Voice random ON")

async def voice_off_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    voice_state["enabled"] = False
    await update.message.reply_text("Voice random OFF")
async def auto_status_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    await update.message.reply_text("Los mensajes automaticos de texto estan desactivados. Solo quedan las imagenes.")


async def auto_on_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    telegram_auto_state["enabled"] = False
    await update.message.reply_text("Los mensajes automaticos de texto siguen apagados. Telegram solo enviara imagenes.")


async def auto_off_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)
    telegram_auto_state["enabled"] = False
    await update.message.reply_text("Auto mensajes OFF")


async def voice_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    chat_id = update.effective_chat.id
    history = conversation_state.get(chat_id, [])
    last = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), None)
    if not last:
        await update.message.reply_text("Aun no tengo nada que convertir.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
    try:
        mp3 = eleven_tts_mp3(last, ELEVENLABS_VOICE_ID_VALUE)
        bio = io.BytesIO(mp3)
        bio.name = "bot.mp3"
        await update.message.reply_audio(audio=bio, title=BOT_AUDIO_TITLE)
    except Exception as e:
        await update.message.reply_text(f"ElevenLabs devolvio un error:\n{e}")

async def audio_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")

    try:
        voice_text = generate_random_voice_note()
        mp3 = eleven_tts_mp3(voice_text, ELEVENLABS_VOICE_ID_VALUE)
        bio = io.BytesIO(mp3); bio.name = "bot.mp3"
        await update.message.reply_audio(audio=bio, title=BOT_AUDIO_TITLE)
    except Exception as e:
        await update.message.reply_text(f"Audio fallido:\n{e}")

async def selfie_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    mood = " ".join(context.args).strip() if context.args else ""
    smile_line = ""
    if mood:
        lower = mood.lower()
        if "sonri" in lower or "smile" in lower:
            smile_line = "Expression: warm genuine smile, soft eyes. "
        elif "serio" in lower:
            smile_line = "Expression: serious, calm, confident. "
        elif "tierno" in lower:
            smile_line = "Expression: tender, affectionate, gentle. "
        elif "travieso" in lower or "playful" in lower:
            smile_line = "Expression: mischievous, playful smirk. "
    mood_line = f"Extra mood/style: {mood}. Keep it subtle and natural." if mood else ""
    variant = int(time.time()) % 100000

    ANGLES = [
      "three-quarter angle, phone slightly higher, subtle down-angle",
      "low angle portrait, camera lower, stronger jawline emphasis",
      "mirror portrait, phone partially visible, torso more framed",
      "close-up face crop, eyes centered, shallow depth-of-field",
      "over-the-shoulder angle, soft side light, candid vibe",
    ]

    BACKGROUNDS = [
      "soft lilac-blue gradient, minimal",
      "bathroom mirror vibe, minimal clean tiles, soft light",
      "train window light, subtle motion blur background, minimal",
      "bedroom soft morning light, clean sheets, minimal decor",
      "night city bokeh lights, elegant and subtle",
    ]

    OUTFITS = [
      "white oversized t-shirt, casual",
      "black turtleneck, elegant",
      "soft lilac hoodie, cozy",
      "tank top, athletic",
      "open shirt, tasteful, not explicit",
    ]

    angle = random.choice(ANGLES)
    bg = random.choice(BACKGROUNDS)
    outfit = random.choice(OUTFITS)

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")

    try:
        prompt = f"""
Keep the same person identity, face structure, and overall likeness from the reference image.
Preserve key facial features, hair color, and hair style.
IMPORTANT: Keep the SAME PERSON identity from the reference image.
Do not change facial identity. Maintain the same face proportions, nose shape, lips, eye shape, and overall likeness.
Only change: outfit, lighting, pose, angle, and background.
If you cannot preserve identity, return a very similar version of the reference rather than a different person.
No new person. No different face. No younger/older. Same person only.

Make a NEW portrait with variation in angle/background/outfit, but maintain identity.

{mood_line}
Camera/angle: {angle}
Background: {bg}
Outfit: {outfit}
{smile_line}
Unique variation id: {variant}. Do NOT reuse the same pose/angle/composition as previous images.
If mood requests something, prioritize it over defaults.

Soft cinematic lighting. No text, no watermark.
""".strip()

        image_bytes = xai_image_edit(prompt=prompt, image_url=BOT_IMAGE_REFERENCE_URL)
        bio = io.BytesIO(image_bytes)
        bio.name = "bot_selfie.png"

        await update.message.reply_photo(photo=bio, caption="\U0001F49C")
    except Exception as e:
        await update.message.reply_text(f"Imagen fallida:\n{e}")


async def video_telegram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    raw_mood = " ".join(context.args).strip()
    normalized_mood = raw_mood.lower()
    if normalized_mood in {
        "ultima",
        "última",
        "ultima foto",
        "última foto",
        "ultima foto que te mande",
        "última foto que te mande",
    }:
        mood = ""
    else:
        mood = raw_mood
    await send_video_from_context(update, context, mood)

async def handle_photo_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    message = update.message
    chat = update.effective_chat
    if not message or not chat:
        return

    photos = getattr(message, "photo", None) or []
    if not photos:
        return

    last_telegram_photo_by_chat[chat.id] = photos[-1].file_id

    caption = (message.caption or "").strip()
    if caption.startswith("/video"):
        await video_telegram_cmd(update, context)
        return

    try:
        reaction_emoji = random.choice(["💜", "💛", "🦦"])
        await message.set_reaction(reaction=[ReactionTypeEmoji(reaction_emoji)])
    except Exception:
        logging.debug("No se pudo anadir reaccion a la foto en Telegram")

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")

    try:
        image_url = await telegram_photo_to_data_url(message, context.bot)
        assistant_text = await asyncio.to_thread(build_photo_reply, chat.id, caption, image_url)
    except Exception:
        logging.exception("Error respondiendo a foto en Telegram")
        assistant_text = (
            "Ya guarde tu foto. Si luego quieres animarla, puedes decirme /video ultima."
        )

    await message.reply_text(assistant_text if assistant_text.endswith("\U0001F49C") else assistant_text + "\n\U0001F49C")


async def handle_message_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_telegram(update):
        return await deny_telegram(update)

    chat_id = update.effective_chat.id
    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    natural_video_prompt = parse_natural_video_request(user_text)
    if natural_video_prompt is not None:
        await send_video_from_context(update, context, natural_video_prompt)
        return

    # Try to react to the user's message in chats that support reactions.
    try:
        reaction_emoji = random.choice(["💜", "💛", "🦦"])
        await update.message.set_reaction(reaction=[ReactionTypeEmoji(reaction_emoji)])
    except Exception:
        logging.debug("No se pudo añadir reaccion en este chat/mensaje de Telegram")

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        assistant_text = await asyncio.to_thread(build_assistant_reply, chat_id, user_text)
    except Exception as e:
        logging.exception("Error OpenAI")
        await update.message.reply_text(f"Se produjo un error procesando la respuesta ({e})")
        return

    await update.message.reply_text(assistant_text if assistant_text.endswith("\U0001F49C") else assistant_text + "\n\U0001F49C")

    try:
        if should_send_voice_auto(assistant_text, voice_state):
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")

            voice_text = await asyncio.to_thread(generate_random_voice_note)
            mp3 = await asyncio.to_thread(eleven_tts_mp3, voice_text, ELEVENLABS_VOICE_ID_VALUE)
            bio = io.BytesIO(mp3)
            bio.name = "bot.mp3"
            await update.message.reply_audio(audio=bio, title=BOT_AUDIO_TITLE)

            voice_state["last_voice_at"] = datetime.now(timezone.utc)
            voice_state["count_today"] += 1
    except Exception:
        logging.exception("Auto-voice failed")
async def telegram_auto_loop(app: Application):
    chat_id = TELEGRAM_AUTO_CHAT_ID or ALLOWED_USER_ID_TELEGRAM
    if not chat_id:
        logging.warning("Telegram auto desactivado: falta TELEGRAM_AUTO_CHAT_ID o ALLOWED_USER_ID_TELEGRAM")
        return

    interval_seconds = TELEGRAM_AUTO_INTERVAL_MIN * 60 if TELEGRAM_AUTO_INTERVAL_MIN > 0 else None
    if interval_seconds is None:
        logging.warning("Intervalo auto desactivado: TELEGRAM_AUTO_INTERVAL_MIN <= 0")

    local_tz = _safe_schedule_tz("Telegram schedule")

    next_interval_at = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds) if interval_seconds else None

    await asyncio.sleep(15)
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(local_tz)
            today_utc = _today_key()
            local_date_key = now_local.strftime("%Y-%m-%d")
            month_key = now_local.strftime("%Y-%m")
            night_key = _night_window_key(now_local)

            if telegram_auto_state["day"] != today_utc:
                telegram_auto_state["day"] = today_utc
                telegram_auto_state["count_today"] = 0

            if telegram_auto_state["night_key"] != night_key:
                telegram_auto_state["night_key"] = night_key
                telegram_auto_state["night_count"] = 0

            if TELEGRAM_RANDOM_IMAGE_ENABLED:
                needs_new_schedule = (
                    telegram_auto_state["next_random_image_at"] is None
                    or telegram_auto_state["random_image_target_date"] is None
                    or telegram_auto_state["last_random_image_date"] == telegram_auto_state["random_image_target_date"]
                    or telegram_auto_state["random_image_target_date"] < local_date_key
                )
                if needs_new_schedule:
                    target_date, scheduled_at = _schedule_random_image_at(now_local, local_tz)
                    telegram_auto_state["random_image_target_date"] = target_date
                    telegram_auto_state["next_random_image_at"] = scheduled_at

            if interval_seconds and next_interval_at and now_utc >= next_interval_at:
                next_interval_at = now_utc + timedelta(seconds=interval_seconds)

            if TELEGRAM_RANDOM_IMAGE_ENABLED:
                next_random_image_at = telegram_auto_state["next_random_image_at"]
                target_date = telegram_auto_state["random_image_target_date"]
                if (
                    next_random_image_at is not None
                    and target_date is not None
                    and telegram_auto_state["last_random_image_date"] != target_date
                    and now_utc >= next_random_image_at
                ):
                    image_bytes, caption = await asyncio.to_thread(generate_daily_random_image)
                    bio = io.BytesIO(image_bytes)
                    bio.name = "bot_daily.png"
                    await app.bot.send_photo(chat_id=chat_id, photo=bio)
                    telegram_auto_state["last_random_image_date"] = target_date
                    telegram_auto_state["next_random_image_at"] = None

        except Exception:
            logging.exception("Telegram auto message failed")

        await asyncio.sleep(20)


# ============================================================
 # START FUNCTIONS
 # ============================================================

async def start_telegram_bot():
    if not TELEGRAM_AVAILABLE:
        logging.warning("Telegram bot desactivado: faltan dependencias de python-telegram-bot")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN_VALUE).build()

    app.add_handler(CommandHandler("start", start_telegram_cmd))
    app.add_handler(CommandHandler("reset", reset_telegram_cmd))
    app.add_handler(CommandHandler("whoami", whoami_telegram_cmd))
    app.add_handler(CommandHandler("voice_status", voice_status_telegram_cmd))
    app.add_handler(CommandHandler("voice_on", voice_on_telegram_cmd))
    app.add_handler(CommandHandler("voice_off", voice_off_telegram_cmd))
    app.add_handler(CommandHandler("auto_status", auto_status_telegram_cmd))
    app.add_handler(CommandHandler("auto_on", auto_on_telegram_cmd))
    app.add_handler(CommandHandler("auto_off", auto_off_telegram_cmd))
    app.add_handler(CommandHandler("voice", voice_telegram_cmd))
    app.add_handler(CommandHandler("audio", audio_telegram_cmd))
    app.add_handler(CommandHandler("selfie", selfie_telegram_cmd))
    app.add_handler(CommandHandler("video", video_telegram_cmd))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_telegram))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_telegram))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    auto_task = asyncio.create_task(telegram_auto_loop(app))
    logging.info(
        "Telegram scheduler arrancado: auto_enabled=%s, random_image=%s, chat_id=%s",
        TELEGRAM_AUTO_ENABLED,
        TELEGRAM_RANDOM_IMAGE_ENABLED,
        TELEGRAM_AUTO_CHAT_ID or ALLOWED_USER_ID_TELEGRAM,
    )

    try:
        await asyncio.Event().wait()
    finally:
        auto_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await auto_task


async def run_service(name: str, coro_factory, retry_delay: int = 10):
    while True:
        try:
            logging.info("%s starting...", name)
            await coro_factory()
            logging.warning("%s stopped unexpectedly; restarting in %ss", name, retry_delay)
        except Exception:
            logging.exception("%s crashed; restarting in %ss", name, retry_delay)
        await asyncio.sleep(retry_delay)


async def main_async():
    tasks = []

    # Start Telegram bot
    if TELEGRAM_BOT_TOKEN_VALUE:
        tasks.append(asyncio.create_task(run_service("Telegram Bot", start_telegram_bot)))
        logging.info("Starting Telegram bot...")
    else:
        logging.warning("Telegram bot desactivado: falta TELEGRAM_BOT_TOKEN")

    if not tasks:
        raise RuntimeError("No hay bot de Telegram configurado")

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=False)
        return


if __name__ == "__main__":
    asyncio.run(main_async())
