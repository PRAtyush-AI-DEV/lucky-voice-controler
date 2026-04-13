"""
ai_chat.py — Gemini API Integration
====================================
Acts as the brain of the assistant when local commands don't match or the user explicitly asks a question.
"""

import os
import logging
import time
import json
import re

try:
    from google import genai as genai
except ImportError:
    genai = None

logger = logging.getLogger("Lucky.Actions.AIChat")

# Keep track of conversation history in memory for context
_chat_session = None
_current_api_key = None
_GEMINI_COOLDOWN_UNTIL = 0.0  # 10 min pause after 429
_genai_client = None
MODEL_NAME = "gemini-1.5-pro"
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-pro"]
_active_model_name = None


def _get_api_key(config: dict) -> str:
    return (os.getenv("GEMINI_API_KEY", "") or config.get("gemini_api_key", "") or "").strip()


def _ensure_session(config: dict) -> tuple[bool, str]:
    """Ensure chat session exists; return (ok, error_message)."""
    global _chat_session, _current_api_key, _genai_client, _GEMINI_COOLDOWN_UNTIL, _active_model_name

    if not genai:
        logger.error("google-genai module not installed.")
        return False, "Gemini AI module installed nahi hai. Kripya requirements install karein."

    now = time.time()
    if now < _GEMINI_COOLDOWN_UNTIL:
        return False, "Thodi der mein poochho, abhi busy hoon."

    api_key = _get_api_key(config)
    if not api_key:
        logger.warning("Gemini API key not found in config/env.")
        return False, "Gemini API key configure nahi hui hai. Kripya GEMINI_API_KEY set karein ya Settings/Config update karein."

    if _chat_session is not None and _current_api_key == api_key and _genai_client is not None:
        return True, ""

    logger.info("Initializing Gemini Session...")
    _current_api_key = api_key

    system_instruction = (
        "You are Lucky, a smart, friendly, and highly capable virtual assistant running on a Windows PC. "
        "You were created by the user to help them with tasks and answer their questions. "
        "IMPORTANT RULES: "
        "1. You must respond in a natural, spoken Hinglish (Hindi written in English alphabet) or Hindi. "
        "2. Your responses will be read out loud by a Text-to-Speech engine, so DO NOT use markdown, emojis, asterisks (*), or complex formatting. Keep plain text. "
        "3. Keep your answers very concise and conversational (1-2 short sentences max) unless the user asks for a detailed explanation. "
        "4. Act like a helpful friend, not a robot."
    )

    try:
        _genai_client = genai.Client(api_key=api_key)
        last_err = None
        for model_name in FALLBACK_MODELS:
            try:
                _chat_session = _genai_client.chats.create(
                    model=model_name,
                    config={"system_instruction": system_instruction},
                )
                _active_model_name = model_name
                logger.info(f"Gemini model selected: {model_name}")
                return True, ""
            except Exception as e:
                last_err = e
                continue
        raise last_err or Exception("No Gemini model available")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {e}")
        return False, "Maafi chahunga, AI model load nahi ho paya."


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON object extraction from model text."""
    if not text:
        return None
    text = text.strip()
    # Try direct JSON first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try fenced block or first {...}
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def route_command(user_text: str, config: dict, allowed_intents: list[str]) -> dict:
    """
    Use Gemini to map free-form command to an allowed intent.
    Returns:
      {
        "intent": str | "UNKNOWN",
        "entity": any,
        "confidence": float (0-1),
        "reply": str (optional, for chat),
        "needs_confirm": bool
      }
    """
    ok, err = _ensure_session(config)
    if not ok:
        return {"intent": "UNKNOWN", "entity": None, "confidence": 0.0, "reply": err, "needs_confirm": False}

    intent_list = ", ".join(sorted(set(allowed_intents)))
    prompt = (
        "Convert the user's spoken command into ONE action intent from this allowlist.\n"
        f"ALLOWLIST: {intent_list}\n\n"
        "Return ONLY valid JSON in this exact schema:\n"
        "{\n"
        '  "intent": "ONE_OF_ALLOWLIST_OR_UNKNOWN",\n'
        '  "entity": null_or_value,\n'
        '  "confidence": 0.0_to_1.0,\n'
        '  "needs_confirm": true_or_false,\n'
        '  "reply": "short_hinglish_reply_or_empty"\n'
        "}\n\n"
        "Rules:\n"
        "- If user is asking a general question (not an OS action), set intent to AI_CHAT and entity to the question.\n"
        "- If you are unsure, set intent UNKNOWN and confidence <= 0.4.\n"
        "- For dangerous actions (shutdown, restart, unlock), set needs_confirm true.\n"
        "- Keep reply short Hinglish.\n\n"
        f'USER: "{user_text}"'
    )

    try:
        logger.info(f"[ROUTER] Routing: '{user_text}'")
        resp = _chat_session.send_message(prompt)
        raw = (getattr(resp, "text", "") or "").strip()
        data = _extract_json(raw) or {}
        intent = str(data.get("intent", "UNKNOWN") or "UNKNOWN").strip()
        entity = data.get("entity", None)
        try:
            conf = float(data.get("confidence", 0.0) or 0.0)
        except Exception:
            conf = 0.0
        needs_confirm = bool(data.get("needs_confirm", False))
        reply = str(data.get("reply", "") or "").strip()
        return {
            "intent": intent,
            "entity": entity,
            "confidence": max(0.0, min(1.0, conf)),
            "needs_confirm": needs_confirm,
            "reply": reply,
        }
    except Exception as e:
        msg = str(e)
        if ("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("quota" in msg.lower()):
            global _GEMINI_COOLDOWN_UNTIL
            _GEMINI_COOLDOWN_UNTIL = time.time() + 600  # 10 min cooldown
            logger.error(f"Gemini quota/rate limit hit; cooling down 10m: {msg}")
            return {
                "intent": "UNKNOWN",
                "entity": None,
                "confidence": 0.0,
                "reply": "Bhai, AI ka quota khatam ho gaya. Thodi der baad try karo ya plan/billing check karo.",
                "needs_confirm": False,
            }
        logger.error(f"Gemini router error: {e}")
        return {"intent": "UNKNOWN", "entity": None, "confidence": 0.0, "reply": "", "needs_confirm": False}


def ask_gemini(query: str, config: dict) -> str:
    """Send query to Gemini and return the spoken response."""
    ok, err = _ensure_session(config)
    if not ok:
        return err

    # Send message to Gemini
    try:
        logger.info(f"Asking Gemini: '{query}'")
        response = _chat_session.send_message(query)
        text = (getattr(response, "text", "") or "").strip()
        
        # Strip out any hallucinated markdown just in case
        text = text.replace("*", "").replace("#", "")
        
        logger.info(f"Gemini Response: '{text}'")
        return text or "Maafi chahunga, AI se response nahi aaya."

    except Exception as e:
        msg = str(e)
        # Quota / rate-limit handling: avoid spamming the API and logs.
        if ("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("quota" in msg.lower()):
            _GEMINI_COOLDOWN_UNTIL = time.time() + 600  # 10 minutes
            logger.error(f"Gemini quota/rate limit hit; cooling down 10m: {msg}")
            return "Thodi der mein poochho, abhi busy hoon."

        logger.error(f"Gemini API Error: {e}")
        return "Bhai, network ya API mein kuch problem hai. Main jawaab nahi de paa raha."
