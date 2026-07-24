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
    """List every conference room in the system.

    Purpose:
        Return all conference rooms with their capacity and location. Useful
        as the entry point for a UI that lets a user pick a room to book.

    Args:
        None: This route takes no path or query parameters.

    Returns:
        flask.Response: JSON with HTTP 200 in the shape
            ``{"data": [ {id, name, capacity, location}, ... ],
               "error": None, "status": 200}``.
            ``data`` is an empty list when no rooms exist.

    Examples:
        Example 1 - list rooms from Python (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/rooms").json()["data"][0]
            {'id': 1, 'name': 'Azure Hall', 'capacity': 30, 'location': 'Building A, Floor 3'}

        Example 2 - inside a test client:
            >>> resp = app.test_client().get("/rooms")
            >>> resp.status_code
            200

    Browser:
        http://localhost:5000/rooms

    cURL:
        curl http://localhost:5000/rooms
    """
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Fetch a single conference room by its ID.

    Purpose:
        Look up one room's details. Returns 404 when the room does not exist.

    Args:
        room_id (int): Path parameter. The primary key of the conference room
            to retrieve.

    Returns:
        flask.Response: JSON with HTTP 200 and the room dict on success
            (``{"data": {id, name, capacity, location}, "error": None,
            "status": 200}``), or HTTP 404 with
            ``{"data": None, "error": "Room not found", "status": 404}``.

    Examples:
        Example 1 - fetch room 1 (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/rooms/1").json()["data"]["name"]
            'Azure Hall'

        Example 2 - missing room returns 404:
            >>> import requests
            >>> requests.get("http://localhost:5000/rooms/999").status_code
            404

    Browser:
        http://localhost:5000/rooms/1

    cURL:
        curl http://localhost:5000/rooms/1
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """List the BOOKED (occupied) time slots for a room.

    Purpose:
        Show which times a room is already taken, so callers can see when it
        is unavailable. This is the inverse of ``get_free_slots``. Only
        bookings with status ``'scheduled'`` are counted.

    Args:
        room_id (int): Path parameter. The conference room whose bookings to
            list.
        date (str, optional): Query parameter ``?date=YYYY-MM-DD``. When
            supplied, only bookings that start on that calendar date are
            returned. Omit to return all scheduled bookings for the room.

    Returns:
        flask.Response: JSON with HTTP 200 in the shape
            ``{"data": [ {booking dict}, ... ], "error": None, "status": 200}``,
            or HTTP 400 with an error message if ``date`` is not valid ISO
            ``YYYY-MM-DD``.

    Examples:
        Example 1 - all scheduled bookings for room 1 (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/rooms/1/availability").json()["status"]
            200

        Example 2 - filter to a single day:
            >>> import requests
            >>> r = requests.get("http://localhost:5000/rooms/1/availability",
            ...                  params={"date": "2025-07-01"})
            >>> [b["start_time"] for b in r.json()["data"]]
            ['2025-07-01T18:00:00', '2025-07-01T19:00:00']

    Browser:
        http://localhost:5000/rooms/1/availability
        http://localhost:5000/rooms/1/availability?date=2025-07-01

    cURL:
        curl "http://localhost:5000/rooms/1/availability"
        curl "http://localhost:5000/rooms/1/availability?date=2025-07-01"
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
    """List the AVAILABLE (unbooked) time slots for a room on one day.

    Purpose:
        Divide the business day (09:00-18:00) into fixed 30-minute slots and
        return only the slots that do not overlap any scheduled booking. This
        is the inverse of ``get_availability`` and is what a "when can I book
        this room?" screen would call.

    Args:
        room_id (int): Path parameter. The conference room to inspect. A
            non-existent room yields HTTP 404.
        date (str, optional): Query parameter ``?date=YYYY-MM-DD``. The day to
            compute free slots for. Defaults to the server's current date when
            omitted.

    Returns:
        flask.Response: JSON with HTTP 200 in the shape
            ``{"data": [ {"start_time": ISO8601, "end_time": ISO8601}, ... ],
            "error": None, "status": 200}`` - one entry per free 30-minute
            slot. Returns HTTP 404 if the room is unknown, or HTTP 400 if
            ``date`` is not valid ISO ``YYYY-MM-DD``.

    Examples:
        Example 1 - free slots for room 1 on a specific day (requests):
            >>> import requests
            >>> r = requests.get("http://localhost:5000/rooms/1/free-slots",
            ...                  params={"date": "2025-07-01"})
            >>> len(r.json()["data"])
            18

        Example 2 - default to today (no date param):
            >>> import requests
            >>> requests.get("http://localhost:5000/rooms/1/free-slots").json()["status"]
            200

    Browser:
        http://localhost:5000/rooms/1/free-slots
        http://localhost:5000/rooms/1/free-slots?date=2025-07-01

    cURL:
        curl "http://localhost:5000/rooms/1/free-slots"
        curl "http://localhost:5000/rooms/1/free-slots?date=2025-07-01"
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
