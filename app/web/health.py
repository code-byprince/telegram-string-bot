"""
Minimal Flask app.

Render (and most PaaS providers) expect a web service to bind to a port and
respond to HTTP requests for health checks. The actual bot logic runs via
Pyrogram in the same process on a background thread; this Flask app exists
purely so Render considers the service "up".
"""

from flask import Flask, jsonify

from app.utils.stats import stats

flask_app = Flask(__name__)


@flask_app.get("/")
def root():
    return jsonify(status="ok", service="telegram-session-generator-bot")


@flask_app.get("/health")
def health():
    return jsonify(
        status="healthy",
        uptime_seconds=round(stats.uptime_seconds, 1),
        total_users=stats.total_users,
    )
