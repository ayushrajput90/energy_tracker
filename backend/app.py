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

    # Auto-create tables within application context
    with app.app_context():
        try:
            db.create_all()
            print(f"[Database] Initialized tables successfully. Engine: {app.config.get('DB_ENGINE_TYPE')}")
        except Exception as e:
            print(f"[Database Warning] Error creating tables: {e}")

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
