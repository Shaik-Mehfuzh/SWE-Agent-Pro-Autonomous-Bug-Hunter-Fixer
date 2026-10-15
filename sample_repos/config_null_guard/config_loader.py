"""
App configuration loader
"""

def load_setting(config, key, default=None):
    # Defect: throws TypeError if config is None
    return config[key]

def list_keys(config):
    if not config:
        return []
    return sorted(list(config.keys()))
