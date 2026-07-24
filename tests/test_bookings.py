"""Tests for the /bookings endpoints (GET, POST, PUT, DELETE).

All tests use the ``client`` fixture from conftest.py, which provides a Flask
test client on an in-memory database seeded with room id 1 and employee id 1
and no bookings. Every response follows the envelope
``{"data": ..., "error": ..., "status": <code>}``.
"""

ROOM_ID = 1
ORGANIZER_ID = 1


def _payload(start='2025-07-10T14:00:00', end='2025-07-10T15:00:00', **overrides):
    """Build a valid create-booking JSON body, with optional field overrides."""
    body = {
        'room_id': ROOM_ID,
        'organizer_id': ORGANIZER_ID,
        'start_time': start,
        'end_time': end,
        'meeting_title': 'Design Review',
        'attendees': 6,
    }
    body.update(overrides)
    return body


def _create(client, **overrides):
    """Helper: POST a booking and return the parsed JSON response."""
    return client.post('/bookings', json=_payload(**overrides))


# --------------------------------------------------------------------------- #
# POST /bookings
# --------------------------------------------------------------------------- #

def test_create_booking_success(client):
    """Success: a valid booking is created and returned with HTTP 201."""
    resp = client.post('/bookings', json=_payload())
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['status'] == 201
    assert body['error'] is None
    assert body['data']['room_id'] == ROOM_ID
    assert body['data']['status'] == 'scheduled'
    assert body['data']['id'] is not None


def test_create_booking_missing_field_returns_400(client):
    """Error: omitting a required field is rejected with HTTP 400."""
    payload = _payload()
    del payload['end_time']
    resp = client.post('/bookings', json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['status'] == 400
    assert body['error'] == 'Missing field: end_time'
    assert body['data'] is None


def test_create_booking_conflict_returns_409(client):
    """Error: a booking overlapping an existing one is rejected with HTTP 409."""
    first = client.post('/bookings', json=_payload(start='2025-07-10T14:00:00',
                                                   end='2025-07-10T15:00:00'))
    assert first.status_code == 201
    # 14:30-15:30 overlaps the tail of the first booking
    resp = client.post('/bookings', json=_payload(start='2025-07-10T14:30:00',
                                                  end='2025-07-10T15:30:00'))
    assert resp.status_code == 409
    body = resp.get_json()
    assert body['status'] == 409
    assert 'conflict' in body['error'].lower()


# --------------------------------------------------------------------------- #
# GET /bookings  (and GET /bookings/<id>)
# --------------------------------------------------------------------------- #

def test_get_bookings_success(client):
    """Success: the collection lists created bookings and supports filtering."""
    _create(client)

    resp = client.get('/bookings')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 200
    assert len(body['data']) == 1

    # room_id filter returns the same booking; a different room returns none
    assert len(client.get('/bookings?room_id=1').get_json()['data']) == 1
    assert client.get('/bookings?room_id=999').get_json()['data'] == []


def test_get_single_booking_not_found_returns_404(client):
    """Error: fetching a non-existent booking returns HTTP 404."""
    resp = client.get('/bookings/999')
    assert resp.status_code == 404
    body = resp.get_json()
    assert body['status'] == 404
    assert body['error'] == 'Booking not found'
    assert body['data'] is None


# --------------------------------------------------------------------------- #
# PUT /bookings/<id>
# --------------------------------------------------------------------------- #

def test_reschedule_booking_success(client):
    """Success: rescheduling to a free window updates the times (HTTP 200)."""
    booking_id = _create(client).get_json()['data']['id']

    resp = client.put(f'/bookings/{booking_id}', json={
        'start_time': '2025-07-10T16:00:00',
        'end_time': '2025-07-10T17:00:00',
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 200
    assert body['data']['start_time'] == '2025-07-10T16:00:00'
    assert body['data']['end_time'] == '2025-07-10T17:00:00'


def test_reschedule_booking_not_found_returns_404(client):
    """Error: rescheduling a non-existent booking returns HTTP 404."""
    resp = client.put('/bookings/999', json={
        'start_time': '2025-07-10T16:00:00',
        'end_time': '2025-07-10T17:00:00',
    })
    assert resp.status_code == 404
    body = resp.get_json()
    assert body['status'] == 404
    assert body['error'] == 'Booking not found'


def test_reschedule_booking_bad_range_returns_400(client):
    """Error: end_time not after start_time is rejected with HTTP 400."""
    booking_id = _create(client).get_json()['data']['id']
    resp = client.put(f'/bookings/{booking_id}', json={
        'start_time': '2025-07-10T17:00:00',
        'end_time': '2025-07-10T16:00:00',
    })
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'end_time must be after start_time'


# --------------------------------------------------------------------------- #
# DELETE /bookings/<id>
# --------------------------------------------------------------------------- #

def test_cancel_booking_success(client):
    """Success: cancelling soft-deletes the booking (status -> cancelled)."""
    booking_id = _create(client).get_json()['data']['id']

    resp = client.delete(f'/bookings/{booking_id}')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 200
    assert body['data']['status'] == 'cancelled'

    # the row still exists (soft delete), now marked cancelled
    fetched = client.get(f'/bookings/{booking_id}').get_json()['data']
    assert fetched['status'] == 'cancelled'


def test_cancel_booking_not_found_returns_404(client):
    """Error: cancelling a non-existent booking returns HTTP 404."""
    resp = client.delete('/bookings/999')
    assert resp.status_code == 404
    body = resp.get_json()
    assert body['status'] == 404
    assert body['error'] == 'Booking not found'
