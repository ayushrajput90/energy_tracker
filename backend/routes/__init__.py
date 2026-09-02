from backend.routes.auth import auth_bp
from backend.routes.energy import energy_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.analytics import analytics_bp
from backend.routes.goals import goals_bp
from backend.routes.activities import activities_bp
from backend.routes.settings import settings_bp
from backend.routes.sources import sources_bp
from backend.routes.generation import generation_bp
from backend.routes.storage import storage_bp

__all__ = [
    'auth_bp',
    'energy_bp',
    'dashboard_bp',
    'analytics_bp',
    'goals_bp',
    'activities_bp',
    'settings_bp',
    'sources_bp',
    'generation_bp',
    'storage_bp'
]
