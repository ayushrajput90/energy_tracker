import os
import socket
from datetime import timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def is_mysql_reachable(uri: str) -> bool:
    """Checks whether the MySQL host and port in the URI are reachable."""
    try:
        if not uri.startswith('mysql'):
            return True
        parsed = urlparse(uri)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except Exception:
        return False

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'renewable-energy-tracker-secret-key-2026')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-super-secret-key-renewable-tracker-2026')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_ACCESS_EXPIRES_DAYS', '7')))
    
    # Target MySQL connection URI
    MYSQL_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:password@localhost:3306/renewable_energy_db'
    )
    SQLITE_URI = 'sqlite:///renewable_energy.db'

    # Auto-detect reachable database engine
    if is_mysql_reachable(MYSQL_URI) or os.environ.get('FORCE_MYSQL', '').lower() == 'true':
        SQLALCHEMY_DATABASE_URI = MYSQL_URI
        DB_ENGINE_TYPE = 'MySQL'
    else:
        SQLALCHEMY_DATABASE_URI = SQLITE_URI
        DB_ENGINE_TYPE = 'SQLite (Local Dev Mode - MySQL server not running on localhost:3306)'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurable calculation defaults
    DEFAULT_GRID_EMISSION_FACTOR = float(os.environ.get('DEFAULT_GRID_EMISSION_FACTOR', '0.82')) # kg CO2 / kWh
    DEFAULT_ELECTRICITY_TARIFF = float(os.environ.get('DEFAULT_ELECTRICITY_TARIFF', '0.15'))     # Currency / kWh
    
    # CORS Origins
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DB_ENGINE_TYPE = 'SQLite (In-Memory Testing)'
