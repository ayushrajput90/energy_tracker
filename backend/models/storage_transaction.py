from datetime import datetime, timezone, date
from backend.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class RenewableStorageTransaction(db.Model):
    __tablename__ = 'renewable_storage_transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey('renewable_sources.id', ondelete='SET NULL'), nullable=True)
    transaction_type = db.Column(db.String(20), nullable=False) # 'SURPLUS', 'CONSUME', 'ADJUSTMENT'
    amount_kwh = db.Column(db.Float, nullable=False)
    reference_record_id = db.Column(db.Integer, db.ForeignKey('energy_records.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index('idx_user_storage_date', 'user_id', 'date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if isinstance(self.date, (date, datetime)) else str(self.date),
            'source_id': self.source_id,
            'transaction_type': self.transaction_type,
            'amount_kwh': round(self.amount_kwh, 4),
            'reference_record_id': self.reference_record_id,
            'notes': self.notes or '',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
