from datetime import datetime, timezone, date
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

GOAL_TYPES = [
    'Energy Generation',
    'Renewable Consumption',
    'Renewable Percentage',
    'CO2 Reduction/Avoidance',
    'Grid Electricity Displacement',
    'Cost Savings'
]

GOAL_STATUSES = ['Active', 'Completed', 'Expired']

class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    goal_type = db.Column(db.String(50), nullable=False)
    target_value = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'goal_type': self.goal_type,
            'target_value': round(self.target_value, 2),
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, (date, datetime)) else str(self.start_date),
            'end_date': self.end_date.isoformat() if isinstance(self.end_date, (date, datetime)) else str(self.end_date),
            'description': self.description or '',
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
