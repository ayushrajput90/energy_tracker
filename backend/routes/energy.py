import csv
import io
from datetime import datetime, date
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.energy_record import EnergyRecord, RENEWABLE_SOURCES
from backend.models.renewable_source import RenewableSource
from backend.models.storage_transaction import RenewableStorageTransaction
from backend.models.user_settings import UserSettings
from backend.models.activity import Activity
from backend.services.calculations import (
    calculate_record_metrics,
    aggregate_record_list,
    calculate_surplus
)
from backend.services.aggregation import (
    parse_date_range,
    get_filtered_records_query,
    calculate_user_storage_balance
)
from backend.utils.validators import validate_date, validate_numeric

energy_bp = Blueprint('energy', __name__, url_prefix='/api/energy')

@energy_bp.route('', methods=['GET'])
@jwt_required()
def list_records():
    user_id = int(get_jwt_identity())
    
    # Query parameters
    source = request.args.get('source')
    time_filter = request.args.get('time_filter')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Pagination
    page = request.args.get('page', type=int)
    limit = request.args.get('limit', type=int)

    # Date range parsing
    start_date, end_date = parse_date_range(time_filter, start_date_str, end_date_str)

    # Base query
    query = get_filtered_records_query(user_id, source=source, start_date=start_date, end_date=end_date)

    # Keyword search across notes and renewable source
    if search:
        query = query.filter(
            db.or_(
                EnergyRecord.renewable_source.ilike(f'%{search}%'),
                EnergyRecord.notes.ilike(f'%{search}%')
            )
        )

    # Fetch user emission factor & tariff for calculations
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    tariff = settings.electricity_tariff if settings else 0.15

    # Overall filtered records for summary calculation
    all_filtered = query.all()
    summary = aggregate_record_list(all_filtered, emission_factor=emission_factor, default_tariff=tariff)

    # Sorting
    sort_col = getattr(EnergyRecord, sort_by, EnergyRecord.date)
    if sort_order.lower() == 'asc':
        query = query.order_by(sort_col.asc(), EnergyRecord.id.asc())
    else:
        query = query.order_by(sort_col.desc(), EnergyRecord.id.desc())

    # Pagination handling
    if page and limit:
        total_items = query.count()
        records_page = query.offset((page - 1) * limit).limit(limit).all()
        records_data = [calculate_record_metrics(r, emission_factor) for r in records_page]
        return jsonify({
            'records': records_data,
            'summary': summary,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_items': total_items,
                'total_pages': (total_items + limit - 1) // limit
            }
        }), 200
    else:
        # Return all records
        records_data = [calculate_record_metrics(r, emission_factor) for r in all_filtered]
        return jsonify({
            'records': records_data,
            'summary': summary,
            'total_items': len(records_data)
        }), 200


@energy_bp.route('', methods=['POST'])
@jwt_required()
def create_record():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Validation
    date_str = data.get('date')
    valid_date, date_err = validate_date(date_str)
    if not valid_date:
        return jsonify({'error': date_err}), 400

    source = data.get('renewable_source', '').strip()
    if not source:
        return jsonify({'error': 'Renewable source is required'}), 400

    v_gen, gen_val, gen_err = validate_numeric(data.get('energy_generated_kwh', 0), 'Energy generated')
    if not v_gen:
        return jsonify({'error': gen_err}), 400

    v_ren, ren_val, ren_err = validate_numeric(data.get('renewable_energy_consumed_kwh', 0), 'Renewable energy consumed')
    if not v_ren:
        return jsonify({'error': ren_err}), 400

    v_grid, grid_val, grid_err = validate_numeric(data.get('grid_energy_consumed_kwh', 0), 'Grid energy consumed')
    if not v_grid:
        return jsonify({'error': grid_err}), 400

    v_stor, storage_used_val, stor_err = validate_numeric(data.get('storage_used_kwh', 0), 'Storage used')
    if not v_stor or storage_used_val < 0:
        return jsonify({'error': stor_err or 'Storage used must be non-negative.'}), 400

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    default_tariff = settings.electricity_tariff if settings else 0.15
    v_tar, tariff_val, tar_err = validate_numeric(data.get('electricity_tariff', default_tariff), 'Tariff')
    if not v_tar:
        return jsonify({'error': tar_err}), 400

    notes = data.get('notes', '').strip()
    record_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Verify storage consumption does not exceed available storage balance
    current_storage_balance = calculate_user_storage_balance(user_id)
    if storage_used_val > current_storage_balance:
        return jsonify({
            'error': f"Cannot use {storage_used_val:.2f} kWh from storage. Available storage balance is {current_storage_balance:.2f} kWh."
        }), 400

    source_id = data.get('source_id')
    is_override = bool(data.get('is_override', False))
    auto_gen_val = float(data.get('automatic_generation_kwh', gen_val))
    override_gen_val = float(data.get('override_generation_kwh')) if data.get('override_generation_kwh') is not None else None

    # Calculate surplus
    surplus_val = calculate_surplus(gen_val, ren_val)
    ending_storage_balance = current_storage_balance + surplus_val - storage_used_val

    # Create new independent record
    record = EnergyRecord(
        user_id=user_id,
        source_id=source_id,
        date=record_date,
        renewable_source=source,
        energy_generated_kwh=gen_val,
        renewable_energy_consumed_kwh=ren_val,
        grid_energy_consumed_kwh=grid_val,
        storage_used_kwh=storage_used_val,
        surplus_kwh=surplus_val,
        storage_balance_kwh=max(0.0, ending_storage_balance),
        is_override=is_override,
        automatic_generation_kwh=auto_gen_val,
        override_generation_kwh=override_gen_val,
        electricity_tariff=tariff_val,
        notes=notes
    )
    record.calculate_total_consumed()

    db.session.add(record)
    db.session.flush()

    # Record storage transactions (surplus and/or consumed)
    if surplus_val > 0:
        tx_surplus = RenewableStorageTransaction(
            user_id=user_id,
            date=record_date,
            source_id=source_id,
            transaction_type='SURPLUS',
            amount_kwh=surplus_val,
            reference_record_id=record.id,
            notes=f"Surplus generated on {date_str} ({source})"
        )
        db.session.add(tx_surplus)

    if storage_used_val > 0:
        tx_consume = RenewableStorageTransaction(
            user_id=user_id,
            date=record_date,
            source_id=source_id,
            transaction_type='CONSUME',
            amount_kwh=storage_used_val,
            reference_record_id=record.id,
            notes=f"Storage utilized on {date_str}"
        )
        db.session.add(tx_consume)
    
    # Log activity
    Activity.log(
        user_id=user_id,
        action_type='ADD_RECORD',
        description=f"Added {source} record for {date_str}: {gen_val:.1f} kWh generated, {ren_val:.1f} kWh consumed, {surplus_val:.1f} kWh surplus"
    )
    db.session.commit()

    emission_factor = settings.co2_emission_factor if settings else 0.82
    return jsonify({
        'message': 'Energy record saved successfully',
        'record': calculate_record_metrics(record, emission_factor)
    }), 201


@energy_bp.route('/<int:record_id>', methods=['GET'])
@jwt_required()
def get_record(record_id: int):
    user_id = int(get_jwt_identity())
    record = EnergyRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82

    return jsonify({'record': calculate_record_metrics(record, emission_factor)}), 200


@energy_bp.route('/<int:record_id>', methods=['PUT'])
@jwt_required()
def update_record(record_id: int):
    user_id = int(get_jwt_identity())
    record = EnergyRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    data = request.get_json() or {}

    if 'date' in data:
        valid_date, date_err = validate_date(data['date'])
        if not valid_date:
            return jsonify({'error': date_err}), 400
        record.date = datetime.strptime(data['date'], "%Y-%m-%d").date()

    if 'renewable_source' in data and data['renewable_source'].strip():
        record.renewable_source = data['renewable_source'].strip()

    if 'energy_generated_kwh' in data:
        v, val, err = validate_numeric(data['energy_generated_kwh'], 'Energy generated')
        if not v:
            return jsonify({'error': err}), 400
        record.energy_generated_kwh = val

    if 'renewable_energy_consumed_kwh' in data:
        v, val, err = validate_numeric(data['renewable_energy_consumed_kwh'], 'Renewable consumed')
        if not v:
            return jsonify({'error': err}), 400
        record.renewable_energy_consumed_kwh = val

    if 'grid_energy_consumed_kwh' in data:
        v, val, err = validate_numeric(data['grid_energy_consumed_kwh'], 'Grid consumed')
        if not v:
            return jsonify({'error': err}), 400
        record.grid_energy_consumed_kwh = val

    if 'storage_used_kwh' in data:
        v, val, err = validate_numeric(data['storage_used_kwh'], 'Storage used')
        if not v:
            return jsonify({'error': err}), 400
        record.storage_used_kwh = val

    if 'electricity_tariff' in data:
        v, val, err = validate_numeric(data['electricity_tariff'], 'Tariff')
        if not v:
            return jsonify({'error': err}), 400
        record.electricity_tariff = val

    if 'notes' in data:
        record.notes = data['notes'].strip()

    record.surplus_kwh = calculate_surplus(record.energy_generated_kwh, record.renewable_energy_consumed_kwh)
    record.calculate_total_consumed()
    
    Activity.log(
        user_id=user_id,
        action_type='UPDATE_RECORD',
        description=f'Updated {record.renewable_source} record #{record.id}'
    )
    db.session.commit()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82

    return jsonify({
        'message': 'Record updated successfully',
        'record': calculate_record_metrics(record, emission_factor)
    }), 200


@energy_bp.route('/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_record(record_id: int):
    user_id = int(get_jwt_identity())
    record = EnergyRecord.query.filter_by(id=record_id, user_id=user_id).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    src = record.renewable_source
    d_str = str(record.date)
    
    # Remove associated storage transactions
    RenewableStorageTransaction.query.filter_by(reference_record_id=record.id).delete()

    db.session.delete(record)
    Activity.log(
        user_id=user_id,
        action_type='DELETE_RECORD',
        description=f'Deleted {src} record for {d_str}'
    )
    db.session.commit()

    return jsonify({'message': 'Record deleted successfully'}), 200


@energy_bp.route('/export/csv', methods=['GET'])
@jwt_required()
def export_csv():
    user_id = int(get_jwt_identity())
    records = EnergyRecord.query.filter_by(user_id=user_id).order_by(EnergyRecord.date.desc(), EnergyRecord.id.desc()).all()

    settings = UserSettings.query.filter_by(user_id=user_id).first()
    emission_factor = settings.co2_emission_factor if settings else 0.82
    curr_sym = settings.currency_symbol if settings else '₹'

    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        'Record ID',
        'Date',
        'Renewable Source',
        'Generation Mode',
        'Energy Generated (kWh)',
        'Renewable Consumed (kWh)',
        'Storage Used (kWh)',
        'Surplus (kWh)',
        'Grid Consumed (kWh)',
        'Total Consumed (kWh)',
        'Renewable (%)',
        f'Electricity Tariff ({curr_sym}/kWh)',
        'Estimated CO2 Avoided (kg)',
        'Estimated Grid Displaced (kWh)',
        f'Estimated Cost Savings ({curr_sym})',
        'Notes'
    ])

    for r in records:
        m = calculate_record_metrics(r, emission_factor)
        mode = 'Manual Override' if r.is_override else 'Automatic'
        writer.writerow([
            m['id'],
            m['date'],
            m['renewable_source'],
            mode,
            m['energy_generated_kwh'],
            m['renewable_energy_consumed_kwh'],
            m.get('storage_used_kwh', 0.0),
            m.get('surplus_kwh', 0.0),
            m['grid_energy_consumed_kwh'],
            m['total_energy_consumed_kwh'],
            f"{m['renewable_percentage']}%",
            m['electricity_tariff'],
            m['co2_avoided_kg'],
            m['grid_displaced_kwh'],
            f"{curr_sym}{m['estimated_savings']:.2f}",
            m['notes']
        ])

    csv_data = output.getvalue()
    filename = f"energy_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )
