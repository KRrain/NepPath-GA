import json
from pathlib import Path
from datetime import datetime

PERMISSIONS_FILE = Path("data/permissions.json")

def get_timestamp():
    """Returns the current UTC time as an ISO 8601 string."""
    return datetime.utcnow().isoformat()

def load_config():
    """Loads the permissions config file."""
    if PERMISSIONS_FILE.exists():
        try:
            with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass  # Fallback to default if file is corrupt or unreadable
    
    # Default structure
    return {"global": {"disabled": False}, "roles": {}, "users": {}}

def save_config(config):
    """Saves the permissions config file."""
    PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
