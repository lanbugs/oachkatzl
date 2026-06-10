"""Celery worker entry point.

Usage: celery -A worker.celery worker -l info
"""
import mongoengine
from app.celery_app import celery
from app.config import settings

mongoengine.connect(host=settings.MONGO_URI)
