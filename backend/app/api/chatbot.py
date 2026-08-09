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

# Fallback model chain — keep in sync with ai_service.GROQ_FALLBACK_MODELS.
GROQ_MODELS = [
    'openai/gpt-oss-120b',
    'qwen/qwen3.6-27b',
    'openai/gpt-oss-20b',
    'llama-3.1-8b-instant',
    'allam-2-7b',
]

# In-memory conversation history per session (last 10 messages)
_conversations: dict = {}


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks output by reasoning models (qwen3, DeepSeek-R1, etc.)."""
    return re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL).strip()


# Shown when a message is clearly outside cybersecurity (no Groq call).
OUT_OF_SCOPE_REPLY = (
    "I focus on **cybersecurity** topics — incidents, attacks, detection, response, hardening, "
    "compliance basics, careers in infosec, tools like Wireshark/Burp, MITRE, OWASP, and similar. "
    "I can't help with cooking, recipes, general homework, entertainment, or other non-security subjects. "
    "Try asking about a threat, vulnerability, or how to investigate an incident."
)

# Broad allow-list signal — if any match, send to the model (don't pre-reject).
_CYBER_TOPIC_RE = re.compile(
    r'\b('
    r'secur|cyber|siber|keamanan|infosec|hack|threat|serangan|vuln|exploit|malware|ransom|'
    r'phish|firewall|waf|ids|ips|soc|siem|log|incident|block|whitelist|regex|owasp|mitre|'
    r'sql|xss|csrf|injection|brute|password|auth|encrypt|ssl|tls|vpn|ddos|botnet|cve|nmap|'
    r'burp|wireshark|forensic|pentest|audit|patch|harden|blue\s*team|red\s*team|deteksi|'
    r'respons|ip\s*address|\bip\b|port\s*scan|zero\s*day|apt|trojan|rootkit|spyware'
    r')\b',
    re.IGNORECASE,
)

# Obvious off-topic — only reject when _CYBER_TOPIC_RE also finds nothing.
_OFF_TOPIC_RE = re.compile(
    r'\b('
    r'resep|rendang|masak|memasak|masakan|recipe|cooking|cook\b|ingredients|bake\b|baking|'
    r'weather|cuaca|prakiraan\s+cuaca|'
    r'lirik\s+lagu|chord\s+lagu|film\s+terbaru|drakor|k\-drama|'
    r'homework|tugas\s+matematika|kalkulus|fisika\s+dasar'
    r')\b',
    re.IGNORECASE,
)


def _is_clearly_off_topic(message: str) -> bool:
    """Fast guardrail: block only obvious non-cyber requests (e.g. recipes)."""
    text = (message or '').strip()
    if not text:
        return False
    if _CYBER_TOPIC_RE.search(text):
        return False
    return bool(_OFF_TOPIC_RE.search(text))


def _build_system_prompt(model_name: str) -> str:
    """Build a system prompt that includes model self-awareness."""
    return f"""You are a cybersecurity AI assistant embedded in Incidentra, a Web-SOC platform.
Your model identity: you are running as **{model_name}**. If a user asks what model or AI you are, answer truthfully with this model name.

SCOPE — IN SCOPE (answer helpfully):
- Any **cybersecurity / information security** topic: web attacks, network security, malware, phishing, IAM, cryptography basics, SOC workflows, incident response, threat intel, hardening, compliance overview (ISO 27001, NIST at high level), security careers, CTF concepts, blue/red team, common tools (Wireshark, Nmap, Burp, etc.).
- **Incidentra-specific help**: reading incidents, severity, blocking, rate limits, detection rules, regex patterns, log analysis, demo/simulation context.
- Practical regex for detection rules — always put patterns in a fenced code block ready to copy-paste.

SCOPE — OUT OF SCOPE (politely refuse; do NOT answer the substance):
- Cooking, recipes, food, entertainment, sports, dating, general trivia, non-security homework, creative writing unrelated to security, or any topic with no security angle.
- Use a short refusal like: "I only cover cybersecurity topics. Ask me about threats, incidents, detection, or defense."

STYLE: concise, practical, actionable for SME owners and junior analysts. No long essays unless the user asks for depth."""


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

    if _is_clearly_off_topic(user_message):
        return jsonify({
            'reply': OUT_OF_SCOPE_REPLY,
            'session_id': session_id,
            'model_used': 'guardrail',
            'out_of_scope': True,
        })

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
