"""Shared pytest fixtures for the conference room booking test suite."""
import pytest

from app import create_app
from extensions import db
from models import ConferenceRoom, Employee


@pytest.fixture
def client():
    """Flask test client backed by a seeded in-memory SQLite database.

    Builds the app with an in-memory database (so tests never touch
    ``db/bookings.db``), creates the schema, and seeds exactly:

    * one conference room (id 1, "Test Room")
    * one employee (id 1, "Test User")
    * no bookings/appointments

    The fixture yields the client from **inside** an active application
    context, so tests may either drive HTTP endpoints through the client or
    call helpers like ``utils.conflict.check_overlap`` and use ``db.session``
    directly. Each test gets a fresh database (tables are dropped on teardown).

    Yields:
        flask.testing.FlaskClient: A test client for the seeded app.
    """
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })

    with app.app_context():
        db.create_all()

        room = ConferenceRoom(name='Test Room', capacity=10, location='Test Building, Floor 1')
        employee = Employee(name='Test User', email='test.user@corp.com', department='Engineering')
        db.session.add_all([room, employee])
        db.session.commit()

        yield app.test_client()

        db.session.remove()
        db.drop_all()
