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
        return {'id': self.id, 'name': self.name, 'capacity': self.capacity, 'location': self.location}

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='organizer', lazy=True)

    def to_dict(self):
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
