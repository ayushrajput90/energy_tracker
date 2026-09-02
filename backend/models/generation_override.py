from datetime import datetime, timezone, date
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class DailyGenerationOverride(db.Model):
    __tablename__ = 'daily_generation_overrides'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey('renewable_sources.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    automatic_generation_kwh = db.Column(db.Float, nullable=False, default=0.0)
    override_generation_kwh = db.Column(db.Float, nullable=False, default=0.0)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        db.Index('idx_user_source_date_override', 'user_id', 'source_id', 'date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source_id': self.source_id,
            'source_type': self.source.source_type if hasattr(self, 'source') and self.source else None,
            'date': self.date.isoformat() if isinstance(self.date, (date, datetime)) else str(self.date),
            'automatic_generation_kwh': round(self.automatic_generation_kwh, 2),
            'override_generation_kwh': round(self.override_generation_kwh, 2),
            'final_generation_kwh': round(self.override_generation_kwh, 2),
            'reason': self.reason or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
