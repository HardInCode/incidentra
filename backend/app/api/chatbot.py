from flask import Blueprint, request, jsonify, session
import os
import requests
import logging
import json

chatbot_bp = Blueprint('chatbot', __name__)
logger = logging.getLogger(__name__)

from app.api.auth_middleware import verify_token

@chatbot_bp.before_request
def _check_auth():
    return verify_token()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a cybersecurity assistant for SME-Guard, an intelligent Web-SOC platform.
You help IT administrators understand security incidents, write regex detection patterns,
explain attack techniques, and provide security recommendations.
Be concise and practical. When asked to write a regex pattern for detection rules,
always format it ready to copy-paste in a code block.
Keep responses focused and actionable for non-technical SME owners."""

# BUG 10 FIX: 4 fallback models from the screenshot
GROQ_MODELS = [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'meta-llama/llama-guard-4-12b',
]

# In-memory conversation history per session (last 10 messages)
_conversations: dict = {}


def _get_groq_reply(messages: list) -> str:
    from app.services.notification_service import _get_setting
    api_key = _get_setting('GROQ_API_KEY')
    if not api_key:
        return "⚠️ Groq API key not configured. Please set GROQ_API_KEY in your .env file to enable the AI chatbot."

    primary_model = os.getenv('GROQ_MODEL', GROQ_MODELS[0])
    models_to_try = [primary_model] + [m for m in GROQ_MODELS if m != primary_model]

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    for model in models_to_try:
        try:
            payload = {
                'model': model,
                'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}] + messages,
                'max_tokens': 800,
                'temperature': 0.5,
            }
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404 or response.status_code == 400:
                logger.warning(f"Model {model} unavailable, trying next...")
                continue
            raise
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}, trying next...")
            continue

    return "❌ All AI models are currently unavailable. Please try again later."


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
        reply = _get_groq_reply(history)
        history.append({'role': 'assistant', 'content': reply})
        _conversations[session_id] = history[-10:]
        return jsonify({'reply': reply, 'session_id': session_id})
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({'error': 'AI service error', 'reply': f'Sorry, I encountered an error: {str(e)}'}), 500


@chatbot_bp.route('/clear', methods=['POST'])
def clear_history():
    data = request.get_json() or {}
    session_id = data.get('session_id', 'default')
    _conversations.pop(session_id, None)
    return jsonify({'message': 'Conversation cleared'})
