"""
Rate limiter centralizado.
Se inicializa sin app para poder importarse en blueprints sin importar app21.
"""
from flask import request
from flask_limiter import Limiter


def _get_client_ip():
    """Usa X-Forwarded-For si existe (Railway/proxy), si no remote_addr."""
    return request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()


limiter = Limiter(key_func=_get_client_ip, default_limits=[])
