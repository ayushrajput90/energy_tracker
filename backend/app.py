import os
import sys
from flask import Flask, jsonify, send_from_directory
from backend.config import Config
from backend.extensions import db, jwt, cors
from backend.routes import (
    auth_bp,
    energy_bp,
    dashboard_bp,
    analytics_bp,
    goals_bp,
    activities_bp,
    settings_bp,
    sources_bp,
    generation_bp,
    storage_bp
)

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(config_class)

    # Initialize CORS
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(energy_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(sources_bp)
    app.register_blueprint(generation_bp)
    app.register_blueprint(storage_bp)

    # JWT Error handlers
    @jwt.unauthorized_loader
    def unauthorized_response(callback):
        return jsonify({
            'error': 'Missing or invalid authentication token',
            'message': 'Please log in to access this resource'
        }), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token has expired',
            'message': 'Your session has expired. Please log in again.'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_response(callback):
        return jsonify({
            'error': 'Invalid token signature',
            'message': 'Authentication failed. Please log in again.'
        }), 401

    # Serve Frontend static pages
    @app.route('/')
    def serve_index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        full_path = os.path.join(app.static_folder, path)
        if os.path.exists(full_path):
            return send_from_directory(app.static_folder, path)
        # Default fallback
        return send_from_directory(app.static_folder, 'index.html')

    # Global error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    # Auto-create tables and seed default demo user if needed
    with app.app_context():
        try:
            db.create_all()
            # Ensure SQLite schema contains newly added columns if existing DB was created with older schema
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    if 'sqlite' in str(db.engine.url):
                        res = conn.execute(text("PRAGMA table_info(user_settings)")).fetchall()
                        col_names = [r[1] for r in res]
                        if col_names and 'currency_code' not in col_names:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN currency_code VARCHAR(10) DEFAULT 'INR'"))
                            conn.commit()
                        if col_names and 'currency_symbol' not in col_names:
                            conn.execute(text("ALTER TABLE user_settings ADD COLUMN currency_symbol VARCHAR(10) DEFAULT 'INR'"))
                            conn.commit()
            except Exception:
                pass

            print(f"[Database] Initialized tables successfully. Engine: {app.config.get('DB_ENGINE_TYPE')}")
            
            # Auto-seed demo user 'alex@example.com' if not present
            from backend.models.user import User
            from backend.models.user_settings import UserSettings
            from backend.models.renewable_source import RenewableSource, SourceCapacityHistory
            from datetime import date
            
            if not app.config.get('TESTING'):
                demo_user = User.query.filter_by(email='alex@example.com').first()
                if not demo_user:
                    demo_user = User()
                    demo_user.full_name = 'Alex Green'
                    demo_user.email = 'alex@example.com'
                    demo_user.set_password('Password123!')
                    db.session.add(demo_user)
                    db.session.flush()

                    settings = UserSettings()
                    settings.user_id = demo_user.id
                    settings.electricity_tariff = 9.0
                    settings.currency_code = 'INR'
                    settings.currency_symbol = 'INR'
                    settings.co2_emission_factor = 0.82
                    db.session.add(settings)

                    solar = RenewableSource()
                    solar.user_id = demo_user.id
                    solar.source_type = 'Solar'
                    solar.installed_capacity_kw = 5.0
                    solar.expected_daily_generation_kwh = 15.0
                    solar.effective_from = date.today()
                    solar.active = True
                    db.session.add(solar)
                    db.session.flush()

                    hist1 = SourceCapacityHistory()
                    hist1.source_id = solar.id
                    hist1.capacity_kw = 5.0
                    hist1.expected_daily_generation_kwh = 15.0
                    hist1.effective_from = date.today()
                    db.session.add(hist1)

                    wind = RenewableSource()
                    wind.user_id = demo_user.id
                    wind.source_type = 'Wind'
                    wind.installed_capacity_kw = 3.0
                    wind.expected_daily_generation_kwh = 10.0
                    wind.effective_from = date.today()
                    wind.active = True
                    db.session.add(wind)
                    db.session.flush()

                    hist2 = SourceCapacityHistory()
                    hist2.source_id = wind.id
                    hist2.capacity_kw = 3.0
                    hist2.expected_daily_generation_kwh = 10.0
                    hist2.effective_from = date.today()
                    db.session.add(hist2)

                    db.session.commit()
                    print("[Database] Seeded demo user 'alex@example.com' with default sources.")
        except Exception as e:
            try:
                print(f"[Database Warning] Error creating tables/seeding: {e}")
            except Exception:
                print("[Database Warning] Error creating tables/seeding.")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    print(f"==================================================")
    print(f" Renewable Energy Usage Tracker API Server Running")
    print(f" Database Engine: {app.config.get('DB_ENGINE_TYPE')}")
    print(f" URL: http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host='0.0.0.0', port=port, debug=debug)
