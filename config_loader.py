import os
import json

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML may not be installed
    yaml = None


def load_config(path: str) -> dict:
    """Load configuration from a YAML or JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        if path.lower().endswith(('.yaml', '.yml')):
            if yaml is None:
                raise ImportError("PyYAML is required for YAML files")
            return yaml.safe_load(f) or {}
        if path.lower().endswith('.json'):
            return json.load(f)
        raise ValueError('Unsupported configuration format')
