from flask import Blueprint, request, jsonify
from extensions import db
from models import Booking, ConferenceRoom, Employee
from utils.conflict import check_overlap
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)

@bookings_bp.route('/bookings', methods=['GET'])
def get_bookings():
    room_id = request.args.get('room_id', type=int)
    organizer_id = request.args.get('organizer_id', type=int)
    query = Booking.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    if organizer_id:
        query = query.filter_by(organizer_id=organizer_id)
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    required = ['room_id', 'organizer_id', 'start_time', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({'data': None, 'error': f'Missing field: {field}', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(data['room_id'], start, end):
        return jsonify({'data': None, 'error': 'Time slot conflicts with existing booking', 'status': 409}), 409
    booking = Booking(
        room_id=data['room_id'],
        organizer_id=data['organizer_id'],
        start_time=start,
        end_time=end,
        meeting_title=data.get('meeting_title', ''),
        attendees=data.get('attendees', 1),
        status='scheduled'
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 201}), 201

@bookings_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
def reschedule_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(booking.room_id, start, end, exclude_id=booking_id):
        return jsonify({'data': None, 'error': 'New time slot conflicts with existing booking', 'status': 409}), 409
    booking.start_time = start
    booking.end_time = end
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})
