"""
Seed the database with sample data for the workshop.
Run from the project root: python db/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import ConferenceRoom, Employee, Booking
from datetime import datetime, timedelta

def seed():
    """Reset the database and populate it with sample workshop data.

    Purpose:
        Drop all tables, recreate them, and insert a fixed sample set: 5
        conference rooms, 10 employees, and 20 scheduled bookings spread
        across 2025-07-01 to 2025-07-05. Intended for local/workshop use to
        give the API something to serve. Destructive - it wipes existing data.

    Args:
        None: Uses the application factory and hard-coded sample data; takes no
            parameters.

    Returns:
        None: Commits rows to the database as a side effect and prints a
            one-line summary of what was seeded.

    Examples:
        Example 1 - run as a script from the project root:
            $ python db/seed_data.py
            ✓ Seeded 5 rooms, 10 employees, 20 bookings

        Example 2 - call it programmatically:
            >>> from db.seed_data import seed
            >>> seed()  # doctest: +SKIP

    Browser / cURL:
        Not an HTTP endpoint - this is a command-line data loader. Run it in a
        terminal (``python db/seed_data.py``) before starting the server; once
        seeded, verify with ``curl http://localhost:5000/rooms``.
    """
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        rooms = [
            ConferenceRoom(name='Azure Hall', capacity=30, location='Building A, Floor 3'),
            ConferenceRoom(name='Quantum Room', capacity=12, location='Building A, Floor 2'),
            ConferenceRoom(name='Summit Space', capacity=50, location='Building B, Floor 1'),
            ConferenceRoom(name='Innovation Lab', capacity=8, location='Building C, Floor 4'),
            ConferenceRoom(name='Vision Center', capacity=20, location='Building A, Floor 1'),
        ]
        db.session.add_all(rooms)
        db.session.commit()

        employees = [
            Employee(name='Alice Thompson', email='alice.thompson@corp.com', department='Engineering'),
            Employee(name='Bob Martins', email='bob.martins@corp.com', department='Sales'),
            Employee(name='Carol White', email='carol.white@corp.com', department='Marketing'),
            Employee(name='David Kumar', email='david.kumar@corp.com', department='Engineering'),
            Employee(name='Emma Johnson', email='emma.johnson@corp.com', department='HR'),
            Employee(name='Frank Osei', email='frank.osei@corp.com', department='Finance'),
            Employee(name='Grace Li', email='grace.li@corp.com', department='Product'),
            Employee(name='Henry Patel', email='henry.patel@corp.com', department='Engineering'),
            Employee(name='Isabel Cruz', email='isabel.cruz@corp.com', department='Operations'),
            Employee(name='James Wright', email='james.wright@corp.com', department='Marketing'),
        ]
        db.session.add_all(employees)
        db.session.commit()

        base = datetime(2025, 7, 1, 9, 0)
        bookings = []
        slot_pairs = [
            (0, 0), (0, 1), (1, 0), (1, 2),
            (2, 1), (2, 3), (3, 0), (3, 4),
            (4, 2), (4, 3), (0, 4), (1, 5),
            (2, 6), (3, 7), (4, 8), (0, 9),
            (1, 1), (2, 2), (3, 3), (4, 4),
        ]
        for idx, (room_idx, emp_idx) in enumerate(slot_pairs):
            start = base + timedelta(days=idx // 4, hours=9 + (idx % 4) * 1)
            end = start + timedelta(minutes=30)
            booking = Booking(
                room_id=room_idx + 1,
                organizer_id=emp_idx + 1,
                start_time=start,
                end_time=end,
                meeting_title=f'Team Sync {idx + 1}',
                attendees=min(5 + idx % 5, 15),
                status='scheduled'
            )
            bookings.append(booking)
        db.session.add_all(bookings)
        db.session.commit()
        print(f"✓ Seeded {len(rooms)} rooms, {len(employees)} employees, {len(bookings)} bookings")

if __name__ == '__main__':
    seed()
