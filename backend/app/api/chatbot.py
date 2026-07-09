from flask import Blueprint, request, jsonify
import os
import re
import requests
import logging

chatbot_bp = Blueprint('chatbot', __name__)
logger = logging.getLogger(__name__)

from app.api.auth_middleware import verify_token

@chatbot_bp.before_request
def _check_auth():
    return verify_token()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Fallback model chain — tries primary then falls through automatically.
# Removed (deprecated by Groq, decommissioned Aug 16 2026):
#   llama-3.3-70b-versatile, llama-3.1-8b-instant
GROQ_MODELS = [
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'openai/gpt-oss-120b',
    'qwen/qwen3-32b',
    'qwen/qwen3.6-27b',
    'openai/gpt-oss-20b',
]

# In-memory conversation history per session (last 10 messages)
_conversations: dict = {}


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks output by reasoning models (qwen3, DeepSeek-R1, etc.)."""
    return re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL).strip()


def _build_system_prompt(model_name: str) -> str:
    """Build a system prompt that includes model self-awareness."""
    return f"""You are a cybersecurity AI assistant embedded in Incidentra SOC, an intelligent Web-SOC platform.
Your model identity: you are running as **{model_name}**. If a user asks what model or AI you are, answer truthfully with this model name.
You help IT administrators understand security incidents, write regex detection patterns,
explain attack techniques, and provide security recommendations.
Be concise and practical. When asked to write a regex pattern for detection rules,
always format it in a code block ready to copy-paste.
Keep responses focused and actionable for non-technical SME owners."""


def _get_groq_reply(messages: list) -> tuple:
    """
    Call Groq API with fallback chain.
    Returns (reply_text, model_used).
    """
    from app.services.notification_service import _get_setting
    api_key = _get_setting('GROQ_API_KEY')
    if not api_key:
        return (
            "⚠️ Groq API key not configured. Please set GROQ_API_KEY in Settings to enable the AI chatbot.",
            "none",
        )

    primary_model = _get_setting('GROQ_MODEL') or os.getenv('GROQ_MODEL', GROQ_MODELS[0])
    models_to_try = [primary_model] + [m for m in GROQ_MODELS if m != primary_model]

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    for model in models_to_try:
        try:
            payload = {
                'model': model,
                'messages': [{'role': 'system', 'content': _build_system_prompt(model)}] + messages,
                'max_tokens': 800,
                'temperature': 0.5,
            }
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            raw = response.json()['choices'][0]['message']['content'].strip()
            clean = _strip_think_tags(raw)
            logger.info(f"Chatbot replied using model: {model}")
            return clean, model
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (400, 404, 422):
                logger.warning(f"Model {model} unavailable (HTTP {status}), trying next...")
                continue
            raise
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}, trying next...")
            continue

    return ("❌ All AI models are currently unavailable. Please try again later.", "none")


@chatbot_bp.route('/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    context = data.get('context', '')  # Optional incident context
    session_id = data.get('session_id', 'default')

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    # Get or create conversation history for this session
    if session_id not in _conversations:
        _conversations[session_id] = []

    history = _conversations[session_id]

    # If incident context provided, prepend it
    full_message = user_message
    if context:
        full_message = f"[Incident Context: {context}]\n\nQuestion: {user_message}"

    history.append({'role': 'user', 'content': full_message})

    # Keep only last 10 messages
    if len(history) > 10:
        history = history[-10:]
        _conversations[session_id] = history

    try:
        reply, model_used = _get_groq_reply(history)
        history.append({'role': 'assistant', 'content': reply})
        _conversations[session_id] = history[-10:]
        return jsonify({'reply': reply, 'session_id': session_id, 'model_used': model_used})
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({'error': 'AI service error', 'reply': f'Sorry, I encountered an error: {str(e)}'}), 500


@chatbot_bp.route('/clear', methods=['POST'])
def clear_history():
    data = request.get_json() or {}
    session_id = data.get('session_id', 'default')
    _conversations.pop(session_id, None)
    return jsonify({'message': 'Conversation cleared'})
