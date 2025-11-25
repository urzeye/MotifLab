from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.routes.api import api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        return {
            "message": "红墨 AI图文生成器 API",
            "version": "0.1.0",
            "endpoints": {
                "health": "/api/health",
                "outline": "POST /api/outline",
                "generate": "POST /api/generate",
                "images": "GET /api/images/<filename>"
            }
        }

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
