from flask import Blueprint, jsonify
from extensions import db
from models import Employee

employees_bp = Blueprint('employees', __name__)

@employees_bp.route('/employees', methods=['GET'])
def get_employees():
    """List every employee in the system.

    Purpose:
        Return all employees so a client (e.g. the booking UI) can let a user
        pick a meeting organizer.

    Args:
        None: This route takes no path or query parameters.

    Returns:
        flask.Response: JSON with HTTP 200 in the shape
            ``{"data": [ {id, name, email, department}, ... ],
               "error": None, "status": 200}``.

    Examples:
        Example 1 - list employees from Python (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/employees").json()["data"][0]["name"]
            'Alice Thompson'

        Example 2 - inside a test client:
            >>> app.test_client().get("/employees").status_code
            200

    Browser:
        http://localhost:5000/employees

    cURL:
        curl http://localhost:5000/employees
    """
    employees = Employee.query.all()
    return jsonify({'data': [e.to_dict() for e in employees], 'error': None, 'status': 200})

@employees_bp.route('/employees/<int:employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Fetch a single employee by ID.

    Purpose:
        Look up one employee's details. Returns 404 when the employee does not
        exist.

    Args:
        employee_id (int): Path parameter. The primary key of the employee to
            retrieve.

    Returns:
        flask.Response: JSON with HTTP 200 and the employee dict on success, or
            HTTP 404 with
            ``{"data": None, "error": "Employee not found", "status": 404}``.

    Examples:
        Example 1 - fetch employee 1 (requests):
            >>> import requests
            >>> requests.get("http://localhost:5000/employees/1").json()["data"]["department"]
            'Engineering'

        Example 2 - missing employee returns 404:
            >>> import requests
            >>> requests.get("http://localhost:5000/employees/999").status_code
            404

    Browser:
        http://localhost:5000/employees/1

    cURL:
        curl http://localhost:5000/employees/1
    """
    employee = db.session.get(Employee, employee_id)
    if not employee:
        return jsonify({'data': None, 'error': 'Employee not found', 'status': 404}), 404
    return jsonify({'data': employee.to_dict(), 'error': None, 'status': 200})
