# Grok Telegram

Bot de Telegram en Python con Grok/xAI como motor principal.

Incluye:
- chat privado por `user_id`
- memoria conversacional en proceso
- respuestas a fotos
- generacion de voz con ElevenLabs
- retratos e imagen diaria desde una imagen de referencia
- generacion de video desde imagen o prompt

## Requisitos

- Python 3.10+
- Un bot de Telegram
- API key de xAI
- Opcional: ElevenLabs

## Instalacion

```bash
git clone <tu-repo>
cd "Grok Telegram"
pip install -r requirements.txt
cp .env.example .env
```

Rellena `.env` y luego ejecuta:

```bash
python main.py
```

## Variables importantes

Minimas para arrancar:
- `TELEGRAM_BOT_TOKEN`
- `XAI_API_KEY`

Recomendadas:
- `ALLOWED_USER_ID_TELEGRAM` para mantenerlo privado
- `BOT_NAME` para cambiar nombre y tono base
- `CHAT_PARTNER_NAME` si quieres personalizar mejor los prompts

Opcionales:
- `ELEVENLABS_API_KEY` y `ELEVENLABS_VOICE_ID`
- `BOT_IMAGE_REFERENCE_URL` para `/selfie`, `/video` e imagen diaria

## Comandos de Telegram

- `/start`
- `/reset`
- `/whoami`
- `/voice`
- `/audio`
- `/voice_on`
- `/voice_off`
- `/voice_status`
- `/auto_on`
- `/auto_off`
- `/auto_status`
- `/selfie [mood]`
- `/video [prompt]`

## Notas

- El proyecto carga `.env` por defecto.
- Tambien acepta `.env.txt` como compatibilidad legacy.
- No subas tu `.env` al repositorio.

## Estructura

```text
.
|-- main.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```
