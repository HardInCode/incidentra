from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import Incident, DetectionRule, BlockedIP, SeverityLevel
from app.api.auth_middleware import verify_token
from app.i18n.ip_history_strings import (
    resolve_lang,
    empty_history_summary,
    build_pattern_summary,
    format_last_active,
)

ip_history_bp = Blueprint('ip_history', __name__)


@ip_history_bp.before_request
def _check_auth():
    return verify_token()


@ip_history_bp.route('/<ip_address>/history', methods=['GET'])
def get_ip_history(ip_address):
    """Return full IP history from incidents. Query: ?lang=en|id"""
    lang = resolve_lang(request.args.get('lang'))
    # Query semua incidents dari IP ini
    incidents = Incident.query.filter_by(source_ip=ip_address).all()
    total = len(incidents)

    if total == 0:
        # IP tidak ditemukan di incidents, kembalikan data kosong
        blocked_entry = BlockedIP.query.filter_by(ip_address=ip_address, is_whitelist=False).first()
        whitelist_entry = BlockedIP.query.filter_by(ip_address=ip_address, is_whitelist=True).first()
        return jsonify({
            'ip_address': ip_address,
            'total_incidents': 0,
            'first_seen': None,
            'last_seen': None,
            'frequency_per_day': 0.0,
            'top_attack_types': [],
            'top_rules_triggered': [],
            'risk_score': 0,
            'pattern_summary': empty_history_summary(ip_address, lang),
            'is_blocked': blocked_entry is not None,
            'is_whitelisted': whitelist_entry is not None,
            'blocked_id': blocked_entry.id if blocked_entry else None,
            'whitelist_id': whitelist_entry.id if whitelist_entry else None,
            'block_type': blocked_entry.block_type if blocked_entry else None,
            'block_reason': blocked_entry.reason if blocked_entry else None,
            'whitelist_reason': whitelist_entry.reason if whitelist_entry else None,
            'recent_incidents': [],
        })

    # Hitung first_seen dan last_seen
    created_times = [i.created_at for i in incidents]
    first_seen = min(created_times)
    last_seen = max(created_times)

    # Hitung frequency per day
    delta_days = max((last_seen - first_seen).total_seconds() / 86400, 1)
    frequency_per_day = round(total / delta_days, 2)

    # Top attack types (group by attack_type)
    attack_counts = {}
    for i in incidents:
        attack_counts[i.attack_type] = attack_counts.get(i.attack_type, 0) + 1
    top_attack_types = [
        {'attack_type': k, 'count': v}
        for k, v in sorted(attack_counts.items(), key=lambda x: -x[1])
    ]

    # Top rules triggered (join detection_rules via rule_id)
    rule_counts = {}
    for i in incidents:
        if i.rule_id:
            rule = DetectionRule.query.get(i.rule_id)
            if rule:
                name = rule.rule_name
                rule_counts[name] = rule_counts.get(name, 0) + 1
    top_rules_triggered = [
        {'rule_name': k, 'count': v}
        for k, v in sorted(rule_counts.items(), key=lambda x: -x[1])
    ]

    # Risk score: (total * 10) + (critical_count * 20), cap 100
    critical_count = sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL)
    risk_score = min((total * 10) + (critical_count * 20), 100)

    dominant_attack = top_attack_types[0]['attack_type'].replace('_', ' ').title() if top_attack_types else 'Unknown'
    dominant_count = top_attack_types[0]['count'] if top_attack_types else 0

    now = datetime.utcnow()
    diff_seconds = max(0, (now - last_seen).total_seconds())
    last_active_str = format_last_active(diff_seconds, lang)
    days_span = max(int(delta_days), 1)
    pattern_summary = build_pattern_summary(
        total,
        days_span,
        dominant_attack,
        dominant_count,
        last_active_str,
        frequency_per_day,
        critical_count,
        len(attack_counts),
        lang,
    )

    blocked_entry = BlockedIP.query.filter_by(ip_address=ip_address, is_whitelist=False).first()
    whitelist_entry = BlockedIP.query.filter_by(ip_address=ip_address, is_whitelist=True).first()
    is_blocked = blocked_entry is not None
    is_whitelisted = whitelist_entry is not None

    # Recent incidents (max 10, sort desc created_at)
    recent = sorted(incidents, key=lambda i: i.created_at, reverse=True)[:10]
    recent_incidents = [
        {
            'id': i.id,
            'created_at': i.created_at.isoformat() + 'Z',
            'attack_type': i.attack_type,
            'severity': i.severity.value,
            'status': i.status.value,
            'request_path': i.request_path,
        }
        for i in recent
    ]

    return jsonify({
        'ip_address': ip_address,
        'total_incidents': total,
        'first_seen': first_seen.isoformat() + 'Z',
        'last_seen': last_seen.isoformat() + 'Z',
        'frequency_per_day': frequency_per_day,
        'top_attack_types': top_attack_types,
        'top_rules_triggered': top_rules_triggered,
        'risk_score': risk_score,
        'pattern_summary': pattern_summary,
        'is_blocked': is_blocked,
        'is_whitelisted': is_whitelisted,
        'blocked_id': blocked_entry.id if blocked_entry else None,
        'whitelist_id': whitelist_entry.id if whitelist_entry else None,
        'block_type': blocked_entry.block_type if blocked_entry else None,
        'block_reason': blocked_entry.reason if blocked_entry else None,
        'whitelist_reason': whitelist_entry.reason if whitelist_entry else None,
        'recent_incidents': recent_incidents,
    })
