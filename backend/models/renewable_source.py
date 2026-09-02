from datetime import datetime, timezone, date
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class RenewableSource(db.Model):
    __tablename__ = 'renewable_sources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    source_type = db.Column(db.String(50), nullable=False) # Solar, Wind, Hydro, Biomass, Geothermal, Other Renewable
    installed_capacity_kw = db.Column(db.Float, nullable=False, default=0.0)
    expected_daily_generation_kwh = db.Column(db.Float, nullable=False, default=0.0)
    effective_from = db.Column(db.Date, nullable=False, default=date.today)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    capacity_history = db.relationship(
        'SourceCapacityHistory',
        backref='source',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='SourceCapacityHistory.effective_from.asc()'
    )
    overrides = db.relationship(
        'DailyGenerationOverride',
        backref='source',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.Index('idx_user_source_type', 'user_id', 'source_type'),
    )

    def get_effective_config_for_date(self, target_date: date):
        """
        Finds the capacity and expected generation effective on a given date.
        Uses source_capacity_history for historical preservation.
        """
        if not self.active and target_date >= self.updated_at.date():
            # If deactivated, check if date is after deactivation
            pass

        # Look up history items where effective_from <= target_date <= (effective_to or date.max)
        hist = SourceCapacityHistory.query.filter(
            SourceCapacityHistory.source_id == self.id,
            SourceCapacityHistory.effective_from <= target_date
        ).filter(
            db.or_(
                SourceCapacityHistory.effective_to.is_(None),
                SourceCapacityHistory.effective_to >= target_date
            )
        ).order_by(SourceCapacityHistory.effective_from.desc()).first()

        if hist:
            return {
                'capacity_kw': hist.capacity_kw,
                'expected_daily_generation_kwh': hist.expected_daily_generation_kwh,
                'effective_from': hist.effective_from,
                'effective_to': hist.effective_to
            }

        # Fallback to current source values if target_date >= effective_from
        if target_date >= self.effective_from:
            return {
                'capacity_kw': self.installed_capacity_kw,
                'expected_daily_generation_kwh': self.expected_daily_generation_kwh,
                'effective_from': self.effective_from,
                'effective_to': None
            }

        return None

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source_type': self.source_type,
            'installed_capacity_kw': round(self.installed_capacity_kw, 2),
            'expected_daily_generation_kwh': round(self.expected_daily_generation_kwh, 2),
            'effective_from': self.effective_from.isoformat() if isinstance(self.effective_from, (date, datetime)) else str(self.effective_from),
            'active': self.active,
            'history_count': self.capacity_history.count() if hasattr(self, 'capacity_history') and self.capacity_history else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SourceCapacityHistory(db.Model):
    __tablename__ = 'source_capacity_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, db.ForeignKey('renewable_sources.id', ondelete='CASCADE'), nullable=False, index=True)
    capacity_kw = db.Column(db.Float, nullable=False)
    expected_daily_generation_kwh = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index('idx_source_hist_dates', 'source_id', 'effective_from', 'effective_to'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'capacity_kw': round(self.capacity_kw, 2),
            'expected_daily_generation_kwh': round(self.expected_daily_generation_kwh, 2),
            'effective_from': self.effective_from.isoformat() if isinstance(self.effective_from, (date, datetime)) else str(self.effective_from),
            'effective_to': self.effective_to.isoformat() if isinstance(self.effective_to, (date, datetime)) and self.effective_to else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
