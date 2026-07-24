from models import Booking

def check_overlap(room_id, start_time, end_time, exclude_id=None):
    """
    Check whether a proposed booking slot overlaps with any existing
    scheduled bookings for a given conference room.

    Two bookings overlap when one starts before the other ends AND ends
    after the other starts. This uses strict less-than comparisons so that
    back-to-back bookings (e.g. 09:00-09:30 followed by 09:30-10:00)
    are correctly allowed.

    Args:
        room_id:     ID of the conference room whose schedule to check
        start_time:  Proposed booking start (datetime)
        end_time:    Proposed booking end (datetime)
        exclude_id:  Optional booking ID to ignore (used during rescheduling)

    Returns:
        True if an overlap exists, False if the slot is free
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
