from datetime import datetime
from app import db
import enum


class SeverityLevel(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class IncidentStatus(enum.Enum):
    NEW = 'new'
    INVESTIGATING = 'investigating'
    RESOLVED = 'resolved'
    FALSE_POSITIVE = 'false_positive'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='analyst')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    incidents = db.relationship('Incident', backref='assigned_user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() + 'Z',
            'is_active': self.is_active,
        }


class DetectionRule(db.Model):
    __tablename__ = 'detection_rules'

    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(100), nullable=False)
    attack_type = db.Column(db.String(50), nullable=False)
    pattern = db.Column(db.Text, nullable=False)
    severity_level = db.Column(db.Enum(SeverityLevel), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    match_count = db.Column(db.Integer, default=0)

    incidents = db.relationship('Incident', backref='rule', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'attack_type': self.attack_type,
            'pattern': self.pattern,
            'severity_level': self.severity_level.value,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z',
            'match_count': self.match_count,
        }


class Incident(db.Model):
    __tablename__ = 'incidents'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source_ip = db.Column(db.String(45), nullable=False, index=True)
    attack_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.Enum(SeverityLevel), nullable=False, index=True)
    status = db.Column(db.Enum(IncidentStatus), default=IncidentStatus.NEW, index=True)
    raw_payload = db.Column(db.Text)
    request_path = db.Column(db.String(500))
    request_method = db.Column(db.String(10))
    user_agent = db.Column(db.String(500))
    response_code = db.Column(db.Integer)
    rule_id = db.Column(db.Integer, db.ForeignKey('detection_rules.id'), nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    country_code = db.Column(db.String(5), nullable=True)
    abuse_confidence_score = db.Column(db.Integer, nullable=True)

    logs = db.relationship('IncidentLog', backref='incident', lazy=True, cascade='all, delete-orphan')
    explanation = db.relationship('IncidentExplanation', backref='incident', uselist=False, cascade='all, delete-orphan')
    notes = db.relationship('IncidentNote', backref='incident', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_logs=False):
        data = {
            'id': self.id,
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z',
            'source_ip': self.source_ip,
            'attack_type': self.attack_type,
            'severity': self.severity.value,
            'status': self.status.value,
            'raw_payload': self.raw_payload,
            'request_path': self.request_path,
            'request_method': self.request_method,
            'user_agent': self.user_agent,
            'response_code': self.response_code,
            'rule_id': self.rule_id,
            'assigned_to': self.assigned_to,
            'assigned_username': self.assigned_user.username if self.assigned_to and self.assigned_user else None,
            'resolved_at': self.resolved_at.isoformat() + 'Z' if self.resolved_at else None,
            'country_code': self.country_code,
            'abuse_confidence_score': self.abuse_confidence_score,
            'has_explanation': self.explanation is not None,
        }
        if include_logs:
            data['logs'] = [log.to_dict() for log in self.logs]
            data['explanation'] = self.explanation.to_dict() if self.explanation else None
            data['notes'] = [note.to_dict() for note in self.notes]
        return data


class IncidentLog(db.Model):
    __tablename__ = 'incident_logs'

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    action_taken = db.Column(db.String(200), nullable=False)
    action_detail = db.Column(db.Text)
    action_time = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(50), default='system')

    def to_dict(self):
        return {
            'id': self.id,
            'incident_id': self.incident_id,
            'action_taken': self.action_taken,
            'action_detail': self.action_detail,
            'action_time': self.action_time.isoformat() + 'Z',
            'performed_by': self.performed_by,
        }


class IncidentExplanation(db.Model):
    __tablename__ = 'incident_explanations'

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), unique=True, nullable=False)
    ai_summary = db.Column(db.Text, nullable=False)
    threat_explanation = db.Column(db.Text)
    recommended_actions = db.Column(db.Text)
    mitre_technique = db.Column(db.String(100))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    model_used = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'incident_id': self.incident_id,
            'ai_summary': self.ai_summary,
            'threat_explanation': self.threat_explanation,
            'recommended_actions': self.recommended_actions,
            'mitre_technique': self.mitre_technique,
            'generated_at': self.generated_at.isoformat() + 'Z',
            'model_used': self.model_used,
        }


class IncidentNote(db.Model):
    __tablename__ = 'incident_notes'

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incidents.id'), nullable=False)
    note_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50), default='admin')

    def to_dict(self):
        return {
            'id': self.id,
            'incident_id': self.incident_id,
            'note_content': self.note_content,
            'created_at': self.created_at.isoformat() + 'Z',
            'created_by': self.created_by,
        }


class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(80), nullable=False, default='system')
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'ip_address': self.ip_address,
        }


class BlockedIP(db.Model):
    __tablename__ = 'blocked_ips'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(200))
    block_type = db.Column(db.String(20), default='temporary')  # temporary / permanent
    block_time = db.Column(db.DateTime, default=datetime.utcnow)
    expire_time = db.Column(db.DateTime, nullable=True)
    incident_count = db.Column(db.Integer, default=1)
    is_whitelist = db.Column(db.Boolean, default=False)
    is_repeat_offender = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(50), default='system')

    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'reason': self.reason,
            'block_type': self.block_type,
            'block_time': self.block_time.isoformat() + 'Z',
            'expire_time': self.expire_time.isoformat() + 'Z' if self.expire_time else None,
            'incident_count': self.incident_count,
            'is_whitelist': self.is_whitelist,
            'is_repeat_offender': self.is_repeat_offender or False,
            'created_by': self.created_by,
        }
