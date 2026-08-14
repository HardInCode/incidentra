"""
DETECTION RULES API — CRUD detection_rules + signal engine reload.
Ctrl+F: create_rule, rules_dirty, RULES_FLOW, ADD_ATTACK_TYPE

─── Jawaban sidang: "proses tambah rule baru" ───
  1. Admin buka Detection Rules → isi rule_name, attack_type, pattern (regex), severity
  2. handleSave → POST /api/rules/ → create_rule() → INSERT detection_rules (PostgreSQL)
  3. _signal_rules_dirty() → Redis rules_dirty=1
  4. log_monitor thread → analyze() → _maybe_reload_rules() → _load_rules_from_db()
  5. Regex rule analyst di-merge dengan baseline OWASP (kecuali Lab Mode ON)
  6. Log berikutnya yang match → incident + respond (PIPELINE normal)

─── Beda "tambah rule" vs "tambah attack type" ───
  Rule baru     = row baru di detection_rules (type harus sudah dikenal engine)
  Type baru     = edit DETECTION_PATTERNS + attackTypes.js (tidak ada tabel master)
  Pasangan: backend/app/core/detection_engine.py, frontend/src/constants/attackTypes.js

Pasangan frontend: frontend/src/pages/DetectionRules.js
Pasangan engine: backend/app/core/detection_engine.py (_load_rules_from_db)
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import DetectionRule, SeverityLevel
from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit

rules_bp = Blueprint('rules', __name__)


@rules_bp.before_request
def _check_auth():
    return verify_token()  # JWT Bearer — axios interceptor di api.js


@rules_bp.route('/', methods=['GET'])
def list_rules():
    """GET /api/rules/ — DetectionRules.js fetchRules(). Analyst & admin boleh baca."""
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')
    is_active = request.args.get('is_active')
    attack_type = request.args.get('attack_type')

    query = DetectionRule.query

    if is_active is not None:
        active_bool = is_active.lower() == 'true'
        query = query.filter(DetectionRule.is_active == active_bool)

    if attack_type:
        query = query.filter(DetectionRule.attack_type == attack_type)

    col_map = {
        'rule_name': DetectionRule.rule_name,
        'severity_level': DetectionRule.severity_level,
        'created_at': DetectionRule.created_at,
        'match_count': DetectionRule.match_count,
    }
    sort_col = col_map.get(sort_by, DetectionRule.created_at)
    if sort_dir == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    rules = query.all()
    return jsonify([r.to_dict() for r in rules])


def _signal_rules_dirty():
    """RULES_FLOW: flag Redis — log_monitor thread baca saat analyze() berikutnya."""
    try:
        from app.core.detection_engine import get_redis_client
        r = get_redis_client()
        if r:
            r.set('rules_dirty', '1')
    except Exception:
        pass


@rules_bp.route('/', methods=['POST'])
@require_role('admin')  # cuma admin — analyst read-only di UI
def create_rule():
    """RULES_FLOW step 1: INSERT rule baru ke PostgreSQL."""
    data = request.get_json()
    try:
        rule = DetectionRule(
            rule_name=data['rule_name'],
            attack_type=data['attack_type'],       # string — harus ada di DETECTION_PATTERNS / attackTypes.js
            pattern=data['pattern'],               # regex Python — di-compile di detection_engine
            severity_level=SeverityLevel(data['severity_level']),  # severity saat rule ini match
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
        )
        db.session.add(rule)
        db.session.commit()
        log_audit('rule.create', resource_type='rule', resource_id=rule.id, details={'rule_name': rule.rule_name})
        _signal_rules_dirty()  # RULES_FLOW step 2: paksa engine reload tanpa restart backend
        return jsonify(rule.to_dict()), 201
    except (KeyError, ValueError) as e:
        return jsonify({'error': str(e)}), 400


@rules_bp.route('/<int:rule_id>', methods=['PUT'])
@require_role('admin')
def update_rule(rule_id):
    """Edit / toggle is_active — DetectionRules.js handleToggle & openEdit."""
    rule = DetectionRule.query.get_or_404(rule_id)
    data = request.get_json()
    for field in ['rule_name', 'pattern', 'description', 'is_active']:
        if field in data:
            setattr(rule, field, data[field])
    if 'severity_level' in data:
        try:
            rule.severity_level = SeverityLevel(data['severity_level'])
        except ValueError:
            return jsonify({'error': f"Invalid severity_level: {data['severity_level']}"}), 400
    db.session.commit()
    log_audit('rule.update', resource_type='rule', resource_id=rule_id, details={'rule_name': rule.rule_name})
    _signal_rules_dirty()
    return jsonify(rule.to_dict())


@rules_bp.route('/<int:rule_id>', methods=['DELETE'])
@require_role('admin')
def delete_rule(rule_id):
    rule = DetectionRule.query.get_or_404(rule_id)
    name = rule.rule_name
    db.session.delete(rule)
    db.session.commit()
    log_audit('rule.delete', resource_type='rule', resource_id=rule_id, details={'rule_name': name})
    _signal_rules_dirty()
    return jsonify({'message': 'Rule deleted'})
