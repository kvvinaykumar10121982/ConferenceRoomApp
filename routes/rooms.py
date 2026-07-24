from flask import Blueprint, request, jsonify
from extensions import db
from models import ConferenceRoom, Booking
from utils.conflict import check_overlap
from datetime import datetime, timedelta, time

rooms_bp = Blueprint('rooms', __name__)

# Business-day window and slot size used to compute available slots.
BUSINESS_START = time(9, 0)    # 09:00
BUSINESS_END = time(18, 0)     # 18:00
SLOT_MINUTES = 30

@rooms_bp.route('/rooms', methods=['GET'])
def get_rooms():
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """
    Returns a room's booked time slots, optionally filtered by date.
    Optional query param: ?date=YYYY-MM-DD
    """
    date_str = request.args.get('date', type=str)
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled'
    )
    if date_str:
        try:
            target_date = datetime.fromisoformat(date_str).date()
            query = query.filter(db.func.date(Booking.start_time) == target_date)
        except ValueError:
            return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/free-slots', methods=['GET'])
def get_free_slots(room_id):
    """
    Returns the room's available (unbooked) time slots for a single day.

    The business day (09:00-18:00) is divided into fixed 30-minute slots;
    only slots that do not overlap any scheduled booking are returned.

    Optional query param: ?date=YYYY-MM-DD (defaults to today).
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404

    date_str = request.args.get('date', type=str)
    if date_str:
        try:
            target_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400
    else:
        target_date = datetime.now().date()

    free_slots = []
    slot_start = datetime.combine(target_date, BUSINESS_START)
    day_end = datetime.combine(target_date, BUSINESS_END)
    slot_delta = timedelta(minutes=SLOT_MINUTES)
    while slot_start + slot_delta <= day_end:
        slot_end = slot_start + slot_delta
        if not check_overlap(room_id, slot_start, slot_end):
            free_slots.append({
                'start_time': slot_start.isoformat(),
                'end_time': slot_end.isoformat(),
            })
        slot_start = slot_end

    return jsonify({'data': free_slots, 'error': None, 'status': 200})
