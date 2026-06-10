from __future__ import annotations

import mongoengine
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO

socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def init_extensions(app):
    from app.config import settings

    mongoengine.connect(host=settings.MONGO_URI)

    CORS(app, origins=settings.CORS_ORIGINS, supports_credentials=True)

    socketio.init_app(
        app,
        message_queue=settings.REDIS_URL,
        cors_allowed_origins=settings.CORS_ORIGINS,
        async_mode="gevent",
        logger=False,
        engineio_logger=False,
    )

    limiter.init_app(app)
