from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.storage_transaction import RenewableStorageTransaction
from backend.models.activity import Activity
from backend.services.aggregation import calculate_user_storage_balance
from backend.utils.validators import validate_date, validate_numeric

storage_bp = Blueprint('storage', __name__, url_prefix='/api/storage')

@storage_bp.route('', methods=['GET'])
@jwt_required()
def get_storage_overview():
    user_id = int(get_jwt_identity())
    date_str = request.args.get('date')

    as_of = None
    if date_str:
        try:
            as_of = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    current_balance = calculate_user_storage_balance(user_id, as_of_date=as_of)

    all_txs = RenewableStorageTransaction.query.filter_by(user_id=user_id).all()
    total_surplus_stored = sum(t.amount_kwh for t in all_txs if t.transaction_type == 'SURPLUS')
    total_storage_consumed = sum(t.amount_kwh for t in all_txs if t.transaction_type == 'CONSUME')

    return jsonify({
        'available_storage_kwh': round(current_balance, 4),
        'total_surplus_stored_kwh': round(total_surplus_stored, 4),
        'total_storage_consumed_kwh': round(total_storage_consumed, 4),
        'transaction_count': len(all_txs)
    }), 200


@storage_bp.route('/transactions', methods=['GET'])
@jwt_required()
def list_transactions():
    user_id = int(get_jwt_identity())
    tx_type = request.args.get('type') # 'SURPLUS' or 'CONSUME'

    query = RenewableStorageTransaction.query.filter_by(user_id=user_id)
    if tx_type:
        query = query.filter(RenewableStorageTransaction.transaction_type == tx_type.upper().strip())

    txs = query.order_by(RenewableStorageTransaction.date.desc(), RenewableStorageTransaction.id.desc()).all()
    current_balance = calculate_user_storage_balance(user_id)

    return jsonify({
        'available_balance_kwh': round(current_balance, 4),
        'transactions': [t.to_dict() for t in txs],
        'total_count': len(txs)
    }), 200


@storage_bp.route('/consume', methods=['POST'])
@jwt_required()
def consume_storage():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    v_amt, amt_val, amt_err = validate_numeric(data.get('amount_kwh', 0), 'Amount to consume')
    if not v_amt or amt_val <= 0:
        return jsonify({'error': amt_err or 'Storage consumption amount must be greater than zero.'}), 400

    date_str = data.get('date')
    if date_str:
        valid_date, date_err = validate_date(date_str)
        if not valid_date:
            return jsonify({'error': date_err}), 400
        tx_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        tx_date = date.today()

    # Check available storage balance
    current_balance = calculate_user_storage_balance(user_id)
    if amt_val > current_balance:
        return jsonify({
            'error': f"Cannot consume {amt_val:.2f} kWh from storage. Available storage balance is only {current_balance:.2f} kWh."
        }), 400

    notes = data.get('notes', 'Direct storage consumption').strip()
    source_id = data.get('source_id')
    ref_id = data.get('reference_record_id')

    tx = RenewableStorageTransaction(
        user_id=user_id,
        date=tx_date,
        source_id=source_id,
        transaction_type='CONSUME',
        amount_kwh=amt_val,
        reference_record_id=ref_id,
        notes=notes
    )
    db.session.add(tx)

    Activity.log(
        user_id=user_id,
        action_type='STORAGE_CONSUME',
        description=f"Consumed {amt_val:.2f} kWh stored renewable energy for {tx_date.isoformat()}"
    )
    db.session.commit()

    remaining_balance = calculate_user_storage_balance(user_id)
    return jsonify({
        'message': f"Successfully consumed {amt_val:.2f} kWh from renewable energy storage.",
        'consumed_amount_kwh': round(amt_val, 4),
        'remaining_storage_kwh': round(remaining_balance, 4),
        'transaction': tx.to_dict()
    }), 201
