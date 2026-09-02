from datetime import datetime, timezone, date
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

RENEWABLE_SOURCES = [
    'Solar',
    'Wind',
    'Hydro',
    'Biomass',
    'Geothermal',
    'Other Renewable'
]

class EnergyRecord(db.Model):
    __tablename__ = 'energy_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    renewable_source = db.Column(db.String(50), nullable=False)
    energy_generated_kwh = db.Column(db.Float, nullable=False, default=0.0)
    renewable_energy_consumed_kwh = db.Column(db.Float, nullable=False, default=0.0)
    grid_energy_consumed_kwh = db.Column(db.Float, nullable=False, default=0.0)
    total_energy_consumed_kwh = db.Column(db.Float, nullable=False, default=0.0)
    electricity_tariff = db.Column(db.Float, nullable=False, default=0.15)
    source_id = db.Column(db.Integer, db.ForeignKey('renewable_sources.id', ondelete='SET NULL'), nullable=True)
    is_override = db.Column(db.Boolean, default=False, nullable=False)
    automatic_generation_kwh = db.Column(db.Float, nullable=False, default=0.0)
    override_generation_kwh = db.Column(db.Float, nullable=True)
    storage_used_kwh = db.Column(db.Float, nullable=False, default=0.0)
    surplus_kwh = db.Column(db.Float, nullable=False, default=0.0)
    storage_balance_kwh = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Composite indexes for fast filtering and aggregation - NO UNIQUE CONSTRAINTS!
    __table_args__ = (
        db.Index('idx_user_date', 'user_id', 'date'),
        db.Index('idx_user_source', 'user_id', 'renewable_source'),
    )

    def calculate_total_consumed(self):
        """Total electricity consumed = renewable consumed + grid consumed"""
        self.total_energy_consumed_kwh = round(
            (self.renewable_energy_consumed_kwh or 0.0) + (self.grid_energy_consumed_kwh or 0.0),
            4
        )
        return self.total_energy_consumed_kwh

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source_id': self.source_id,
            'date': self.date.isoformat() if isinstance(self.date, (date, datetime)) else str(self.date),
            'renewable_source': self.renewable_source,
            'energy_generated_kwh': round(self.energy_generated_kwh, 4),
            'renewable_energy_consumed_kwh': round(self.renewable_energy_consumed_kwh, 4),
            'grid_energy_consumed_kwh': round(self.grid_energy_consumed_kwh, 4),
            'total_energy_consumed_kwh': round(self.total_energy_consumed_kwh, 4),
            'electricity_tariff': round(self.electricity_tariff, 4),
            'is_override': self.is_override,
            'automatic_generation_kwh': round(self.automatic_generation_kwh or 0.0, 4),
            'override_generation_kwh': round(self.override_generation_kwh, 4) if self.override_generation_kwh is not None else None,
            'storage_used_kwh': round(self.storage_used_kwh or 0.0, 4),
            'surplus_kwh': round(self.surplus_kwh or 0.0, 4),
            'storage_balance_kwh': round(self.storage_balance_kwh or 0.0, 4),
            'notes': self.notes or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
