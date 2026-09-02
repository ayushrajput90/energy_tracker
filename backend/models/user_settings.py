from datetime import datetime, timezone
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class UserSettings(db.Model):
    __tablename__ = 'user_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    electricity_tariff = db.Column(db.Float, default=0.1500, nullable=False) # $/kWh
    co2_emission_factor = db.Column(db.Float, default=0.8200, nullable=False) # kg CO2/kWh
    theme = db.Column(db.String(20), default='light')
    currency_code = db.Column(db.String(10), default='INR') # 'INR', 'USD', 'EUR', 'GBP'
    currency_symbol = db.Column(db.String(10), default='₹')
    notification_preferences = db.Column(db.Boolean, default=True)
    unit_preference = db.Column(db.String(10), default='kWh')
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'electricity_tariff': self.electricity_tariff,
            'co2_emission_factor': self.co2_emission_factor,
            'theme': self.theme,
            'currency_code': self.currency_code or 'INR',
            'currency_symbol': self.currency_symbol or '₹',
            'notification_preferences': self.notification_preferences,
            'unit_preference': self.unit_preference,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
