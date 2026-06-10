"""Celery Beat entry point.

Usage: celery -A beat.celery beat -l info
"""
import mongoengine
from app.celery_app import celery
from app.config import settings

mongoengine.connect(host=settings.MONGO_URI)
