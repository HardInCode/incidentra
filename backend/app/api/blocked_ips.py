"""
BLOCKED IPs API — manual block/unblock + whitelist sync ke vuln-web.
Ctrl+F: UNBLOCK_FLOW, REDIS_ESCALATION, DEDUP, add_blocked, unblock_ip

UNBLOCK_FLOW (demo unblock → attack → block lagi):
  BlockedIPs.js handleUnblock → DELETE /blocked-ips/:id → unblock_ip()
  → REDIS_ESCALATION: salin incident_count ke Redis sebelum DELETE row
  → DEDUP: Redis unblocked:{ip} + hapus unblock_waiver → 1 incident baru per attack_type
  → _write_blocked_ips.json → vuln-web security.py baca blocklist

Triple-write saat auto-block (response_manager):
  PostgreSQL blocked_ips + Redis + blocked_ips.json

Pasangan frontend: frontend/src/pages/BlockedIPs.js
Pasangan response: backend/app/core/response_manager.py (ESCALATING, REDIS_ESCALATION)
Pasangan dedup: backend/app/core/log_monitor.py (DEDUP)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app import db
from app.models import BlockedIP
from app.api.auth_middleware import verify_token, require_role
from app.services.audit_service import log_audit

blocked_ips_bp = Blueprint('blocked_ips', __name__)


@blocked_ips_bp.before_request
def _check_auth():
    return verify_token()


@blocked_ips_bp.route('/', methods=['GET'])
def list_blocked():
    """BlockedIPs.js fetchIPs — tab Blocked / Whitelist via ?whitelist=true."""
    show_whitelist = request.args.get('whitelist', 'false').lower() == 'true'

    sort_by = request.args.get('sort_by', 'block_time')
    sort_dir = request.args.get('sort_dir', 'desc')
    block_type = request.args.get('block_type')  # permanent | temporary
    repeat_offender = request.args.get('repeat_offender', 'false').lower() == 'true'
    search = request.args.get('search', '')

    query = BlockedIP.query.filter_by(is_whitelist=show_whitelist)

    if block_type:
        query = query.filter(BlockedIP.block_type == block_type)

    if repeat_offender:
        query = query.filter(BlockedIP.is_repeat_offender == True)

    if search:
        query = query.filter(BlockedIP.ip_address.ilike(f'%{search}%'))

    col_map = {
        'ip_address': BlockedIP.ip_address,
        'block_time': BlockedIP.block_time,
        'incident_count': BlockedIP.incident_count,  # naik saat ESCALATING block sama IP
    }
    sort_col = col_map.get(sort_by, BlockedIP.block_time)
    if sort_dir == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    items = query.all()
    return jsonify([i.to_dict() for i in items])


@blocked_ips_bp.route('/', methods=['POST'])
@require_role('admin')
def add_blocked():
    """Manual block atau whitelist — BlockedIPs.js handleAdd / handleAddWhitelist."""
    data = request.get_json()
    ip = data.get('ip_address', '').strip()
    if not ip:
        return jsonify({'error': 'ip_address required'}), 400

    is_whitelist = bool(data.get('is_whitelist', False))
    existing = BlockedIP.query.filter_by(ip_address=ip).first()

    if existing and not is_whitelist:
        if existing.is_whitelist:
            return jsonify({
                'error': 'IP is whitelisted. Remove whitelist first or use whitelist endpoint.',
            }), 409
        return jsonify({'error': 'IP already in list'}), 409

    block_type = data.get('block_type', 'permanent')
    expire_time = None
    if block_type == 'temporary' and not is_whitelist:
        hours = int(data.get('hours', 24))
        expire_time = datetime.utcnow() + timedelta(hours=hours)

    if existing and is_whitelist:
        existing.is_whitelist = True
        existing.reason = data.get('reason', 'Whitelisted — trusted IP')
        existing.block_type = 'permanent'
        existing.expire_time = None
        existing.created_by = data.get('created_by', 'admin')
        blocked = existing
        db.session.commit()
        log_audit('blocked_ip.whitelist', resource_type='blocked_ip', resource_id=blocked.id, details={'ip': ip})
    else:
        blocked = BlockedIP(
            ip_address=ip,
            reason=data.get('reason', 'Whitelisted — trusted IP' if is_whitelist else 'Manual block'),
            block_type='permanent' if is_whitelist else block_type,
            expire_time=expire_time,
            is_whitelist=is_whitelist,
            created_by=data.get('created_by', 'admin'),
        )
        db.session.add(blocked)
        db.session.commit()
        log_audit(
            'blocked_ip.whitelist' if is_whitelist else 'blocked_ip.add',
            resource_type='blocked_ip',
            resource_id=blocked.id,
            details={'ip': ip},
        )

    # Sync ke blocked_ips.json — vuln-web middleware/security.py enforce 403
    from app.core.response_manager import _write_blocked_ips_json, clear_rate_limit_entry
    from app.core.detection_engine import get_redis_client
    _write_blocked_ips_json()
    if is_whitelist:
        clear_rate_limit_entry(ip, get_redis_client())  # whitelist = hapus rate limit counter
    return jsonify(blocked.to_dict()), 201 if not existing else 200


@blocked_ips_bp.route('/<int:ip_id>', methods=['DELETE'])
@require_role('admin')
def unblock_ip(ip_id):
    """
    UNBLOCK_FLOW — BlockedIPs.js handleUnblock.
    Urutan penting: salin escalation → DELETE DB → sync JSON → Redis dedup waiver.
    """
    blocked = BlockedIP.query.get_or_404(ip_id)
    ip_address = blocked.ip_address
    was_whitelist = blocked.is_whitelist

    # REDIS_ESCALATION step 1: incident_count DB → Redis (survive DELETE row)
    # Pasangan baca: response_manager._escalating_block() elif redis escalation_count
    if not was_whitelist:
        try:
            from app.core.detection_engine import get_redis_client as _grc
            _r = _grc()
            if _r:
                count = blocked.incident_count or 0
                if count > 0:
                    _r.setex(f"escalation_count:{ip_address}", 30 * 24 * 3600, str(count))
        except Exception:
            pass

    db.session.delete(blocked)
    db.session.commit()

    # UNBLOCK step 2: update blocked_ips.json + clear rate limit Redis entry
    try:
        from app.core.response_manager import _write_blocked_ips_json, clear_rate_limit_entry
        from app.core.detection_engine import get_redis_client
        _write_blocked_ips_json()
        clear_rate_limit_entry(ip_address, get_redis_client())
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not update blocked_ips.json: {e}")

    # DEDUP waiver — log_monitor cek unblocked:{ip} → skip dedup 1x per attack_type
    try:
        from app.core.detection_engine import get_redis_client, clear_brute_force_state
        r = get_redis_client()
        if r:
            r.setex(f"unblocked:{ip_address}", 600, '1')  # flag 10 menit
            for key in r.scan_iter(f"unblock_waiver:{ip_address}:*"):
                r.delete(key)
        clear_brute_force_state(ip_address)  # reset BruteForceTracker counter
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not reset detection state on unblock: {e}")

    log_audit(
        'blocked_ip.unwhitelist' if was_whitelist else 'blocked_ip.unblock',
        resource_type='blocked_ip',
        resource_id=ip_id,
        details={'ip': ip_address},
    )
    return jsonify({
        'message': 'Whitelist removed' if was_whitelist else 'IP unblocked',
        'was_whitelist': was_whitelist,
    })


@blocked_ips_bp.route('/<int:ip_id>', methods=['PATCH'])
@require_role('admin')
def update_blocked(ip_id):
    """Edit reason / block_type / hours — BlockedIPs.js handleEdit."""
    blocked = BlockedIP.query.get_or_404(ip_id)
    if blocked.is_whitelist:
        return jsonify({'error': 'Cannot modify whitelist entry'}), 400

    data = request.get_json() or {}
    block_type = data.get('block_type', blocked.block_type)
    if block_type not in ('permanent', 'temporary'):
        return jsonify({'error': 'block_type must be permanent or temporary'}), 400

    expire_time = None
    if block_type == 'temporary':
        if 'hours' not in data:
            return jsonify({'error': 'hours required for temporary block'}), 400
        try:
            hours = int(data['hours'])
        except (TypeError, ValueError):
            return jsonify({'error': 'hours must be a number'}), 400
        if hours <= 0:
            return jsonify({'error': 'hours must be positive'}), 400
        expire_time = datetime.utcnow() + timedelta(hours=hours)
        if expire_time <= datetime.utcnow():
            return jsonify({'error': 'expire_time must be in the future'}), 400

    if 'reason' in data:
        blocked.reason = data.get('reason') or blocked.reason

    blocked.block_type = block_type
    blocked.expire_time = expire_time

    db.session.commit()

    try:
        from app.core.response_manager import _write_blocked_ips_json
        _write_blocked_ips_json()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not update blocked_ips.json: {e}")

    log_audit(
        'blocked_ip.update',
        resource_type='blocked_ip',
        resource_id=ip_id,
        details={
            'ip': blocked.ip_address,
            'block_type': block_type,
            'expire_time': expire_time.isoformat() if expire_time else None,
        },
    )
    return jsonify(blocked.to_dict())
