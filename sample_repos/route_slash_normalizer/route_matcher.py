"""
HTTP Router URL Matcher
"""

def match_endpoint(request_path, route_pattern):
    # Defect: strict equality fails when trailing slash differs
    if request_path == route_pattern:
        return True
    return False

def get_base_path(request_path):
    parts = [p for p in request_path.split("/") if p]
    return f"/{parts[0]}" if parts else "/"
