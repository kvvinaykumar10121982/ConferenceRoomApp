from flask import Blueprint, request, jsonify
from extensions import db
from models import Booking, ConferenceRoom, Employee
from utils.conflict import check_overlap
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)

@bookings_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """List bookings, optionally filtered by room and/or organizer.

    Purpose:
        Return all bookings, or a subset filtered by room and/or organizer.
        Both filters are optional and combine with AND when supplied together.

    Args:
        room_id (int, optional): Query parameter ``?room_id=``. When set, only
            bookings for this conference room are returned.
        organizer_id (int, optional): Query parameter ``?organizer_id=``. When
            set, only bookings created by this employee are returned.

    Returns:
        flask.Response: JSON with HTTP 200 in the shape
            ``{"data": [ {booking dict}, ... ], "error": None, "status": 200}``.
            ``data`` is an empty list when nothing matches.

    Examples:
        Example 1 - every booking for room 1 (requests):
            >>> import requests
            >>> r = requests.get("http://localhost:5000/bookings",
            ...                  params={"room_id": 1})
            >>> len(r.json()["data"])
            4

        Example 2 - bookings organized by employee 1:
            >>> import requests
            >>> requests.get("http://localhost:5000/bookings",
            ...              params={"organizer_id": 1}).json()["status"]
            200

    Browser:
        http://localhost:5000/bookings
        http://localhost:5000/bookings?room_id=1&organizer_id=1

    cURL:
        curl "http://localhost:5000/bookings"
        curl "http://localhost:5000/bookings?room_id=1&organizer_id=1"
    """
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
    """Fetch a single booking by its ID.

    Purpose:
        Retrieve the full detail of one booking. Returns 404 when it does not
        exist.

    Args:
        booking_id (int): Path parameter. The primary key of the booking to
            retrieve.

    Returns:
        flask.Response: JSON with HTTP 200 and the booking dict on success, or
            HTTP 404 with
            ``{"data": None, "error": "Booking not found", "status": 404}``.

    Examples:
        Example 1 - fetch booking 1 (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/bookings/1").json()["data"]["meeting_title"]
            'Team Sync 1'

        Example 2 - missing booking returns 404:
            >>> import requests
            >>> requests.get("http://localhost:5000/bookings/999").status_code
            404

    Browser:
        http://localhost:5000/bookings/1

    cURL:
        curl http://localhost:5000/bookings/1
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking for a room, rejecting time conflicts.

    Purpose:
        Reserve a room for a time window. The request is validated for
        required fields, ISO-8601 datetimes, a positive duration, and absence
        of overlap with existing scheduled bookings for the same room.

    Args:
        JSON request body (application/json):
            room_id (int): Required. ID of the room to book.
            organizer_id (int): Required. ID of the employee booking the room.
            start_time (str): Required. ISO-8601 start, e.g.
                ``"2025-07-10T14:00:00"``.
            end_time (str): Required. ISO-8601 end; must be after start_time.
            meeting_title (str, optional): Defaults to ``""``.
            attendees (int, optional): Defaults to ``1``.

    Returns:
        flask.Response: HTTP 201 with the created booking dict on success.
            Error paths: HTTP 400 (missing body, missing field, bad datetime,
            or end_time <= start_time) and HTTP 409 (time slot conflicts with
            an existing booking).

    Examples:
        Example 1 - create a booking (requests):
            >>> import requests
            >>> body = {"room_id": 1, "organizer_id": 1,
            ...         "start_time": "2025-07-10T14:00:00",
            ...         "end_time": "2025-07-10T15:00:00",
            ...         "meeting_title": "Design Review", "attendees": 6}
            >>> requests.post("http://localhost:5000/bookings", json=body).status_code
            201

        Example 2 - overlapping slot is rejected with 409:
            >>> import requests
            >>> requests.post("http://localhost:5000/bookings", json=body).status_code
            409

    Browser:
        Not directly callable from a browser address bar (POST with a JSON
        body). Use the browser DevTools console instead:
            fetch("http://localhost:5000/bookings", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({room_id:1, organizer_id:1,
                start_time:"2025-07-10T14:00:00",
                end_time:"2025-07-10T15:00:00"})
            }).then(r => r.json()).then(console.log)

    cURL:
        curl -X POST http://localhost:5000/bookings \\
          -H "Content-Type: application/json" \\
          -d '{"room_id":1,"organizer_id":1,"start_time":"2025-07-10T14:00:00","end_time":"2025-07-10T15:00:00","meeting_title":"Design Review","attendees":6}'
    """
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
    """Reschedule an existing booking to a new time window.

    Purpose:
        Move a booking to a new start/end time. The room and organizer are
        unchanged. The new window is validated for ISO format, positive
        duration, and absence of overlap with other scheduled bookings in the
        same room (the booking being edited is excluded from that check).

    Args:
        booking_id (int): Path parameter. The booking to reschedule.
        JSON request body (application/json):
            start_time (str): Required. New ISO-8601 start time.
            end_time (str): Required. New ISO-8601 end time; must be after
                start_time.

    Returns:
        flask.Response: HTTP 200 with the updated booking dict on success.
            Error paths: HTTP 404 (booking not found), HTTP 400 (no body, bad
            datetime, or end_time <= start_time), HTTP 409 (new slot conflicts
            with another booking).

    Examples:
        Example 1 - reschedule booking 1 (requests):
            >>> import requests
            >>> body = {"start_time": "2025-07-10T16:00:00",
            ...         "end_time": "2025-07-10T17:00:00"}
            >>> requests.put("http://localhost:5000/bookings/1", json=body).status_code
            200

        Example 2 - unknown booking returns 404:
            >>> import requests
            >>> requests.put("http://localhost:5000/bookings/999", json=body).status_code
            404

    Browser:
        Not directly callable from the address bar (PUT with a JSON body). Use
        DevTools console:
            fetch("http://localhost:5000/bookings/1", {
              method: "PUT",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({start_time:"2025-07-10T16:00:00",
                                    end_time:"2025-07-10T17:00:00"})
            }).then(r => r.json()).then(console.log)

    cURL:
        curl -X PUT http://localhost:5000/bookings/1 \\
          -H "Content-Type: application/json" \\
          -d '{"start_time":"2025-07-10T16:00:00","end_time":"2025-07-10T17:00:00"}'
    """
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
    """Cancel a booking (soft delete).

    Purpose:
        Mark a booking as cancelled. This is a soft delete: the row is kept
        but its ``status`` becomes ``'cancelled'``, which frees the slot for
        conflict checks and availability queries (they only consider
        ``'scheduled'`` bookings).

    Args:
        booking_id (int): Path parameter. The booking to cancel.

    Returns:
        flask.Response: HTTP 200 with the updated booking dict (status now
            ``'cancelled'``) on success, or HTTP 404 with
            ``{"data": None, "error": "Booking not found", "status": 404}``.

    Examples:
        Example 1 - cancel booking 1 (requests):
            >>> import requests
            >>> requests.delete("http://localhost:5000/bookings/1").json()["data"]["status"]
            'cancelled'

        Example 2 - cancelling an unknown booking returns 404:
            >>> import requests
            >>> requests.delete("http://localhost:5000/bookings/999").status_code
            404

    Browser:
        Not directly callable from the address bar (DELETE method). Use
        DevTools console:
            fetch("http://localhost:5000/bookings/1", {method: "DELETE"})
              .then(r => r.json()).then(console.log)

    cURL:
        curl -X DELETE http://localhost:5000/bookings/1
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})
