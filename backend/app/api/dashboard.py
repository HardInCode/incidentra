"""
SOC Dashboard API — aggregated stats from PostgreSQL for the React dashboard.
Ctrl+F: get_stats, log_status, _get_system_status

Alur data (hulu → hilir):
  Dashboard.js fetchStats → api.js GET /dashboard/stats → get_stats() di sini
  → JSON stats.* → KPI cards + Chart.js + Globe di frontend

Semua route butuh JWT — before_request verify_token()
"""
from flask import Blueprint, jsonify
from datetime import datetime, timedelta
import json
from sqlalchemy import func, case
from app import db
from app.models import Incident, BlockedIP, SeverityLevel, IncidentStatus
from app.api.auth_middleware import verify_token
from app.core.detection_engine import get_redis_client

dashboard_bp = Blueprint('dashboard', __name__)

_SEVERITY_LEVELS = ('critical', 'high', 'medium', 'low')
DASHBOARD_STATS_CACHE_KEY = 'incidentra:dashboard:stats:v1'
CACHE_TTL = 15  # seconds cache TTL for high performance


def invalidate_dashboard_cache():
    """Invalidate dashboard cache when new incidents occur or data resets."""
    try:
        r = get_redis_client()
        if r:
            r.delete(DASHBOARD_STATS_CACHE_KEY)
    except Exception:
        pass


def _last_n_calendar_days(n: int = 7):
    """UTC calendar days from oldest to newest (inclusive of today)."""
    today = datetime.utcnow().date()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _fill_timeline(rows, days):
    """Map query rows to a full day range with count=0 for missing days."""
    counts = {str(d): c for d, c in rows}
    return [{'date': str(d), 'count': counts.get(str(d), 0)} for d in days]


def _fill_severity_timeline(rows, days):
    """Expand severity timeline to every day × severity with zeros filled in."""
    counts = {(str(d), s.value if hasattr(s, 'value') else s): c for d, s, c in rows}
    filled = []
    for d in days:
        ds = str(d)
        for sev in _SEVERITY_LEVELS:
            filled.append({
                'date': ds,
                'severity': sev,
                'count': counts.get((ds, sev), 0),
            })
    return filled


@dashboard_bp.before_request
def _check_auth():
    return verify_token()


@dashboard_bp.route('/stats', methods=['GET'])
def get_stats():
    """GET /api/dashboard/stats — optimized aggregated stats with Redis cache."""
    # ─── 0. Check Redis Cache First (Instant < 5ms response) ───
    redis_client = get_redis_client()
    if redis_client:
        try:
            cached = redis_client.get(DASHBOARD_STATS_CACHE_KEY)
            if cached:
                return jsonify(json.loads(cached))
        except Exception:
            pass

    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # ─── 1. Single consolidated SQL query for all KPI counters & system health ───
    kpi_row = db.session.query(
        func.count(Incident.id).label('total'),
        func.count(case((Incident.created_at >= last_24h, 1))).label('last_24h'),
        func.count(case((Incident.created_at >= last_7d, 1))).label('last_7d'),
        func.count(case((Incident.status == IncidentStatus.NEW, 1))).label('open'),
        func.count(case((Incident.status == IncidentStatus.RESOLVED, 1))).label('resolved'),
        func.count(case((Incident.severity == SeverityLevel.CRITICAL, 1))).label('critical'),
        func.count(case((Incident.severity == SeverityLevel.HIGH, 1))).label('high'),
        func.count(case(((Incident.severity == SeverityLevel.CRITICAL) & (Incident.status == IncidentStatus.NEW), 1))).label('critical_new'),
        func.count(case(((Incident.severity == SeverityLevel.HIGH) & (Incident.status == IncidentStatus.NEW), 1))).label('high_new'),
    ).first()

    total = (kpi_row.total if kpi_row else 0) or 0
    last_24h_count = (kpi_row.last_24h if kpi_row else 0) or 0
    last_7d_count = (kpi_row.last_7d if kpi_row else 0) or 0
    open_count = (kpi_row.open if kpi_row else 0) or 0
    resolved_count = (kpi_row.resolved if kpi_row else 0) or 0
    critical = (kpi_row.critical if kpi_row else 0) or 0
    high = (kpi_row.high if kpi_row else 0) or 0
    critical_new = (kpi_row.critical_new if kpi_row else 0) or 0
    high_new = (kpi_row.high_new if kpi_row else 0) or 0

    blocked_ips = BlockedIP.query.filter_by(is_whitelist=False).count()

    # ─── System Status (calculated from consolidated KPI query without extra DB hit) ───
    if critical_new > 0:
        system_status = {'status': 'critical', 'label': 'Active Critical Threats', 'color': 'red'}
    elif high_new > 0:
        system_status = {'status': 'warning', 'label': 'Suspicious Activity Detected', 'color': 'yellow'}
    else:
        system_status = {'status': 'normal', 'label': 'All Systems Normal', 'color': 'green'}

    # ─── CHART 5 — Attack Types ───
    attack_breakdown = db.session.query(
        Incident.attack_type, func.count(Incident.id)
    ).group_by(Incident.attack_type).all()

    # ─── CHART 2 — By Severity ───
    severity_breakdown = db.session.query(
        Incident.severity, func.count(Incident.id)
    ).group_by(Incident.severity).all()

    chart_days = _last_n_calendar_days(7)

    # ─── CHART 1 — Incident Timeline (7 days) ───
    timeline_raw = db.session.query(
        func.date(Incident.created_at).label('date'),
        func.count(Incident.id).label('count')
    ).filter(
        Incident.created_at >= last_7d
    ).group_by(func.date(Incident.created_at)).order_by('date').all()

    # ─── CHART 3 — Severity Trend ───
    severity_timeline_raw = db.session.query(
        func.date(Incident.created_at).label('date'),
        Incident.severity,
        func.count(Incident.id).label('count'),
    ).filter(
        Incident.created_at >= last_7d
    ).group_by(func.date(Incident.created_at), Incident.severity).order_by('date').all()

    timeline = _fill_timeline(timeline_raw, chart_days)
    severity_timeline = _fill_severity_timeline(severity_timeline_raw, chart_days)

    # ─── Top Attacking IPs ───
    top_ips = db.session.query(
        Incident.source_ip, func.count(Incident.id).label('count')
    ).group_by(Incident.source_ip).order_by(func.count(Incident.id).desc()).limit(10).all()

    # ─── Globe — Attack Origins ───
    top_countries = db.session.query(
        Incident.country_code,
        func.count(Incident.id).label('count'),
    ).filter(
        Incident.created_at >= last_7d,
        Incident.country_code.isnot(None),
        Incident.country_code != '',
    ).group_by(Incident.country_code).order_by(
        func.count(Incident.id).desc()
    ).limit(20).all()

    geo_enriched_7d = db.session.query(func.count(Incident.id)).filter(
        Incident.created_at >= last_7d,
        Incident.country_code.isnot(None),
        Incident.country_code != '',
    ).scalar() or 0

    # ─── MTTR card (computed directly in SQL via epoch extraction) ───
    try:
        mttr_val = db.session.query(
            func.avg(func.extract('epoch', Incident.resolved_at) - func.extract('epoch', Incident.created_at))
        ).filter(
            Incident.status == IncidentStatus.RESOLVED,
            Incident.resolved_at.isnot(None)
        ).scalar()
        mttr = round((float(mttr_val) if mttr_val else 0) / 60, 1)
    except Exception:
        mttr = 0

    payload = {
        'total_incidents': total,
        'last_24h': last_24h_count,
        'last_7d': last_7d_count,
        'open_incidents': open_count,
        'resolved_incidents': resolved_count,
        'blocked_ips': blocked_ips,
        'critical_count': critical,
        'high_count': high,
        'mttr_minutes': mttr,
        'attack_breakdown': [{'type': t, 'count': c} for t, c in attack_breakdown],
        'severity_breakdown': [{'severity': s.value if hasattr(s, 'value') else str(s), 'count': c} for s, c in severity_breakdown],
        'timeline': timeline,
        'severity_timeline': severity_timeline,
        'top_attacking_ips': [{'ip': ip, 'count': c} for ip, c in top_ips],
        'top_countries': [{'code': code, 'count': c} for code, c in top_countries],
        'geo_enriched_7d': geo_enriched_7d,
        'system_status': system_status,
    }

    # Store in Redis Cache
    if redis_client:
        try:
            redis_client.setex(DASHBOARD_STATS_CACHE_KEY, CACHE_TTL, json.dumps(payload))
        except Exception:
            pass

    return jsonify(payload)


@dashboard_bp.route('/log-status', methods=['GET'])
def log_status():
    """GET /api/dashboard/log-status — stale=true jika tidak ada log > 60 detik."""
    from app.core.log_monitor import get_last_log_received_at, get_log_file_last_activity
    from app.core.detection_engine import get_redis_client

    now = datetime.utcnow()
    redis_client = get_redis_client()

    candidates = [
        get_last_log_received_at(redis_client),
        get_log_file_last_activity(),
    ]
    last_at = max((t for t in candidates if t is not None), default=None)

    if last_at is None:
        seconds_since = None
        stale = True
    else:
        seconds_since = int((now - last_at).total_seconds())
        stale = seconds_since > 60

    return jsonify({
        'last_received_at': (last_at.isoformat() + 'Z') if last_at else None,
        'seconds_since_last_log': seconds_since,
        'stale': stale,
    })


@dashboard_bp.route("/recent-incidents", methods=["GET"])
def recent_incidents():
    """10 incident terbaru — Dashboard sidebar (opsional widget)."""
    incidents = Incident.query.order_by(Incident.created_at.desc()).limit(10).all()
    return jsonify([i.to_dict() for i in incidents])


def _get_system_status():
    """Banner hijau/kuning/merah — berdasarkan incident NEW critical/high."""
    critical_new = Incident.query.filter(
        Incident.severity == SeverityLevel.CRITICAL,
        Incident.status == IncidentStatus.NEW
    ).count()
    high_new = Incident.query.filter(
        Incident.severity == SeverityLevel.HIGH,
        Incident.status == IncidentStatus.NEW
    ).count()

    if critical_new > 0:
        return {'status': 'critical', 'label': 'Active Critical Threats', 'color': 'red'}
    elif high_new > 0:
        return {'status': 'warning', 'label': 'Suspicious Activity Detected', 'color': 'yellow'}
    else:
        return {'status': 'normal', 'label': 'All Systems Normal', 'color': 'green'}
