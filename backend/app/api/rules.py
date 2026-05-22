"""
DETECTION RULES API — CRUD for detection_rules; sets Redis rules_dirty on write.
SIDANG Ctrl+F: update_rule (is_active toggle), create_rule
Pairs with: detection_engine._load_rules_from_db
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import DetectionRule, SeverityLevel
from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit

rules_bp = Blueprint('rules', __name__)


@rules_bp.before_request
def _check_auth():
    return verify_token()


@rules_bp.route('/', methods=['GET'])
def list_rules():
    # REVISI 1B: tambahkan query params untuk sort dan filter
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')
    is_active = request.args.get('is_active')
    attack_type = request.args.get('attack_type')

    query = DetectionRule.query

    # Filter is_active
    if is_active is not None:
        active_bool = is_active.lower() == 'true'
        query = query.filter(DetectionRule.is_active == active_bool)

    # Filter attack_type
    if attack_type:
        query = query.filter(DetectionRule.attack_type == attack_type)

    # Sorting
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


@rules_bp.route('/', methods=['POST'])
@require_role('admin')  # REVISI 3: hanya admin
def create_rule():
    data = request.get_json()
    try:
        rule = DetectionRule(
            rule_name=data['rule_name'],
            attack_type=data['attack_type'],
            pattern=data['pattern'],
            severity_level=SeverityLevel(data['severity_level']),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
        )
        db.session.add(rule)
        db.session.commit()
        log_audit('rule.create', resource_type='rule', resource_id=rule.id, details={'rule_name': rule.rule_name})
        return jsonify(rule.to_dict()), 201
    except (KeyError, ValueError) as e:
        return jsonify({'error': str(e)}), 400


@rules_bp.route('/<int:rule_id>', methods=['PUT'])
@require_role('admin')  # REVISI 3: hanya admin
def update_rule(rule_id):
    rule = DetectionRule.query.get_or_404(rule_id)
    data = request.get_json()
    for field in ['rule_name', 'pattern', 'description', 'is_active']:
        if field in data:
            setattr(rule, field, data[field])
    # BUG 9 FIX: update severity_level correctly
    if 'severity_level' in data:
        try:
            rule.severity_level = SeverityLevel(data['severity_level'])
        except ValueError:
            return jsonify({'error': f"Invalid severity_level: {data['severity_level']}"}), 400
    db.session.commit()
    log_audit('rule.update', resource_type='rule', resource_id=rule_id, details={'rule_name': rule.rule_name})
    # BUG 9 FIX: Signal detection engine to reload rules
    try:
        from app.core.detection_engine import get_redis_client
        r = get_redis_client()
        if r:
            r.set('rules_dirty', '1')
    except Exception:
        pass
    return jsonify(rule.to_dict())


@rules_bp.route('/<int:rule_id>', methods=['DELETE'])
@require_role('admin')  # REVISI 3: hanya admin
def delete_rule(rule_id):
    rule = DetectionRule.query.get_or_404(rule_id)
    name = rule.rule_name
    db.session.delete(rule)
    db.session.commit()
    log_audit('rule.delete', resource_type='rule', resource_id=rule_id, details={'rule_name': name})
    return jsonify({'message': 'Rule deleted'})
