"""
Flask web application for health checks
"""

from flask import Flask, jsonify, request
from app.config import Config
from app.utils.logger import setup_logger
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logger(__name__)

app = Flask(__name__)


@app.route('/')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Telegram String Generator Bot",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced dynamically
    })


@app.route('/health')
def health():
    """Detailed health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "telegram-string-generator-bot",
        "uptime": "N/A"  # Would need to track actual uptime
    })


@app.route('/ready')
def ready():
    """Readiness probe endpoint"""
    # Check if bot is running
    from app.bot import create_app
    
    try:
        bot = create_app()
        if bot.is_running:
            return jsonify({"status": "ready"}), 200
        else:
            return jsonify({"status": "not ready"}), 503
    except:
        return jsonify({"status": "not ready"}), 503


@app.errorhandler(404)
def not_found(e):
    """404 handler"""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """500 handler"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info(f"Starting Flask web server on {Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT)
