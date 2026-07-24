"""
Shared Flask extension instances.

These live here (rather than in app.py) so that models and route modules can
import `db` without importing the application factory. Importing from app.py
would re-execute its module-level `app = create_app()` and cause a circular
import when app.py is run directly.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
