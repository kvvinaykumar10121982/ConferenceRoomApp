from extensions import db
from datetime import datetime

class ConferenceRoom(db.Model):
    __tablename__ = 'conference_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def to_dict(self):
        """Serialize this conference room to a JSON-ready dict.

        Purpose:
            Convert the SQLAlchemy model into plain, JSON-serializable types so
            route handlers can pass it straight to ``jsonify``.

        Args:
            None: Operates on ``self``; takes no parameters.

        Returns:
            dict: ``{"id": int, "name": str, "capacity": int,
                "location": str}``.

        Examples:
            Example 1 - serialize a fetched room:
                >>> room = ConferenceRoom.query.get(1)
                >>> room.to_dict()["name"]
                'Azure Hall'

            Example 2 - serialize a transient (unsaved) instance:
                >>> ConferenceRoom(name='Test', capacity=4,
                ...                location='B1').to_dict()["capacity"]
                4

        Browser / cURL:
            Not called directly over HTTP. Its output is what you see in the
            ``data`` field of ``GET /rooms`` and ``GET /rooms/<id>``, e.g.
            ``curl http://localhost:5000/rooms/1``.
        """
        return {'id': self.id, 'name': self.name, 'capacity': self.capacity, 'location': self.location}

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='organizer', lazy=True)

    def to_dict(self):
        """Serialize this employee to a JSON-ready dict.

        Purpose:
            Convert the SQLAlchemy model into plain, JSON-serializable types
            for use in API responses.

        Args:
            None: Operates on ``self``; takes no parameters.

        Returns:
            dict: ``{"id": int, "name": str, "email": str,
                "department": str}``.

        Examples:
            Example 1 - serialize a fetched employee:
                >>> emp = Employee.query.get(1)
                >>> emp.to_dict()["email"]
                'alice.thompson@corp.com'

            Example 2 - serialize a transient instance:
                >>> Employee(name='Zoe', email='zoe@corp.com',
                ...          department='IT').to_dict()["department"]
                'IT'

        Browser / cURL:
            Not exposed as its own endpoint. Employee data feeds the
            ``organizer_id`` field of bookings; no employee list route exists.
        """
        return {'id': self.id, 'name': self.name, 'email': self.email, 'department': self.department}

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    meeting_title = db.Column(db.String(200))
    attendees = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize this booking to a JSON-ready dict.

        Purpose:
            Convert the SQLAlchemy model into plain, JSON-serializable types,
            rendering the ``start_time`` and ``end_time`` datetimes as ISO-8601
            strings. ``created_at`` is intentionally omitted from the payload.

        Args:
            None: Operates on ``self``; takes no parameters.

        Returns:
            dict: ``{"id": int, "room_id": int, "organizer_id": int,
                "start_time": str (ISO-8601), "end_time": str (ISO-8601),
                "meeting_title": str, "attendees": int, "status": str}``.

        Examples:
            Example 1 - serialize a fetched booking:
                >>> b = Booking.query.get(1)
                >>> b.to_dict()["start_time"]
                '2025-07-01T18:00:00'

            Example 2 - status is included in the payload:
                >>> Booking.query.get(1).to_dict()["status"]
                'scheduled'

        Browser / cURL:
            Not called directly over HTTP. Its output is the ``data`` element
            returned by the ``/bookings`` routes, e.g.
            ``curl http://localhost:5000/bookings/1``.
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'organizer_id': self.organizer_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'meeting_title': self.meeting_title,
            'attendees': self.attendees,
            'status': self.status
        }
