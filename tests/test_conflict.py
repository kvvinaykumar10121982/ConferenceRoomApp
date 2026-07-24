"""Tests for utils.conflict.check_overlap.

The seeded fixture (see conftest.py) provides room id 1 and employee id 1 with
no bookings. Each test inserts a single existing booking from 10:00 to 11:00 on
2025-07-01, then probes a proposed window against it.

check_overlap returns True when the proposed window collides with an existing
*scheduled* booking, and False when the slot is free. Comparisons are strict
(``<`` / ``>``), so back-to-back bookings do NOT count as a conflict.
"""
from datetime import datetime

from extensions import db
from models import Booking
from utils.conflict import check_overlap

ROOM_ID = 1
ORGANIZER_ID = 1


def _dt(hour, minute=0):
    """Build a datetime on the fixed test date 2025-07-01."""
    return datetime(2025, 7, 1, hour, minute)


def _add_existing_booking(status='scheduled'):
    """Insert the reference booking (10:00-11:00) used by every test."""
    booking = Booking(
        room_id=ROOM_ID,
        organizer_id=ORGANIZER_ID,
        start_time=_dt(10),
        end_time=_dt(11),
        meeting_title='Existing meeting',
        attendees=1,
        status=status,
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def test_no_overlap(client):
    """(1) A window entirely after the existing booking is free."""
    _add_existing_booking()
    # existing 10:00-11:00, proposed 12:00-13:00 -> no overlap
    assert check_overlap(ROOM_ID, _dt(12), _dt(13)) is False


def test_exact_overlap(client):
    """(2) A window identical to the existing booking conflicts."""
    _add_existing_booking()
    # existing 10:00-11:00, proposed 10:00-11:00 -> conflict
    assert check_overlap(ROOM_ID, _dt(10), _dt(11)) is True


def test_partial_overlap(client):
    """(3) A window that overlaps only part of the booking conflicts."""
    _add_existing_booking()
    # proposed 10:30-11:30 overlaps the tail end of 10:00-11:00
    assert check_overlap(ROOM_ID, _dt(10, 30), _dt(11, 30)) is True
    # proposed 09:30-10:30 overlaps the front end of 10:00-11:00
    assert check_overlap(ROOM_ID, _dt(9, 30), _dt(10, 30)) is True


def test_back_to_back_is_not_a_conflict(client):
    """(4) Adjacent windows that only touch at an endpoint are NOT conflicts."""
    _add_existing_booking()
    # proposed 11:00-12:00 starts exactly when the existing booking ends
    assert check_overlap(ROOM_ID, _dt(11), _dt(12)) is False
    # proposed 09:00-10:00 ends exactly when the existing booking starts
    assert check_overlap(ROOM_ID, _dt(9), _dt(10)) is False


def test_one_booking_fully_contains_another(client):
    """(5) Full containment (either direction) is a conflict."""
    _add_existing_booking()
    # proposed 09:00-12:00 fully contains the existing 10:00-11:00
    assert check_overlap(ROOM_ID, _dt(9), _dt(12)) is True
    # proposed 10:15-10:45 is fully contained within the existing 10:00-11:00
    assert check_overlap(ROOM_ID, _dt(10, 15), _dt(10, 45)) is True
