from models import Booking

def check_overlap(room_id, start_time, end_time, exclude_id=None):
    """Check whether a proposed time slot collides with existing bookings.

    Purpose:
        Decide if a room is free for a proposed window. Two bookings overlap
        when one starts before the other ends AND ends after the other starts.
        Strict less-than comparisons are used so back-to-back bookings (e.g.
        09:00-09:30 followed by 09:30-10:00) are allowed, not flagged. Only
        bookings with status ``'scheduled'`` are considered, so cancelled
        bookings never block a slot. This helper backs both booking creation
        and rescheduling, and the ``/rooms/<id>/free-slots`` route.

    Args:
        room_id (int): ID of the conference room whose schedule to check.
        start_time (datetime.datetime): Proposed booking start.
        end_time (datetime.datetime): Proposed booking end.
        exclude_id (int, optional): A booking ID to ignore during the check.
            Used when rescheduling so a booking does not conflict with itself.
            Defaults to None.

    Returns:
        bool: ``True`` if any scheduled booking overlaps the window (the slot
            is taken), ``False`` if the slot is free.

    Examples:
        Example 1 - probe a slot before creating a booking:
            >>> from datetime import datetime
            >>> check_overlap(1, datetime(2025, 7, 1, 18, 0),
            ...                   datetime(2025, 7, 1, 18, 30))
            True

        Example 2 - ignore the booking being rescheduled:
            >>> from datetime import datetime
            >>> check_overlap(1, datetime(2025, 7, 1, 18, 0),
            ...                   datetime(2025, 7, 1, 18, 30), exclude_id=1)
            False

    Browser / cURL:
        Not an HTTP endpoint - this is an internal helper called by the
        booking routes. To exercise its logic over HTTP, POST a booking and
        watch for a 409 conflict, e.g.::

            curl -X POST http://localhost:5000/bookings \\
              -H "Content-Type: application/json" \\
              -d '{"room_id":1,"organizer_id":1,"start_time":"2025-07-01T18:00:00","end_time":"2025-07-01T18:30:00"}'
    """
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None
