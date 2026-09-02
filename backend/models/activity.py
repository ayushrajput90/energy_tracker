from datetime import datetime, timezone
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    action_type = db.Column(db.String(50), nullable=False) # e.g. 'REGISTER', 'LOGIN', 'ADD_RECORD', etc.
    description = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)

    @classmethod
    def log(cls, user_id: int, action_type: str, description: str):
        activity = cls(user_id=user_id, action_type=action_type, description=description)
        db.session.add(activity)
        return activity

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
