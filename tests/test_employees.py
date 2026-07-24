"""Tests for the /employees endpoints and the SPA index route.

Uses the ``client`` fixture from conftest.py (in-memory DB seeded with one
employee, id 1).
"""


def test_get_employees_success(client):
    """Success: the collection lists the seeded employee (HTTP 200)."""
    resp = client.get('/employees')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['status'] == 200
    assert body['error'] is None
    assert len(body['data']) == 1
    assert body['data'][0]['email'] == 'test.user@corp.com'


def test_get_single_employee_success(client):
    """Success: an existing employee is returned by ID (HTTP 200)."""
    resp = client.get('/employees/1')
    assert resp.status_code == 200
    assert resp.get_json()['data']['name'] == 'Test User'


def test_get_employee_not_found_returns_404(client):
    """Error: an unknown employee returns HTTP 404."""
    resp = client.get('/employees/999')
    assert resp.status_code == 404
    body = resp.get_json()
    assert body['status'] == 404
    assert body['error'] == 'Employee not found'


def test_index_serves_spa(client):
    """The root route serves the single-page UI as HTML."""
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'text/html' in resp.content_type
    assert b'Conference Room Booking' in resp.data
