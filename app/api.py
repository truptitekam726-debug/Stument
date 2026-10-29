
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify
from flask_login import login_required

from app.extensions import db
from app.models import Employee, Department

api_bp = Blueprint("api", __name__)


def employee_json(employee):
    return {
        "id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "job_title": employee.job_title,
        "salary": str(employee.salary),
        "joining_date": employee.joining_date.isoformat(),
        "department": employee.department.name,
        "is_active": employee.is_active,
    }


@api_bp.get("/employees")
@login_required
def list_employees():
    employees = Employee.query.order_by(Employee.id.desc()).all()
    return jsonify([employee_json(e) for e in employees])


@api_bp.get("/employees/<int:employee_id>")
@login_required
def get_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    return jsonify(employee_json(employee))


@api_bp.post("/employees")
@login_required
def create_employee():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="A JSON object is required."), 400

    required = ("name", "email", "job_title", "department_id", "salary", "joining_date")
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify(error="Missing fields.", fields=missing), 400

    name = str(data["name"]).strip()
    email = str(data["email"]).strip().lower()
    job_title = str(data["job_title"]).strip()

    if not name or len(name) > 120:
        return jsonify(error="Invalid name."), 400

    if not email or len(email) > 150 or "@" not in email:
        return jsonify(error="Invalid email."), 400

    if not job_title or len(job_title) > 100:
        return jsonify(error="Invalid job title."), 400

    if Employee.query.filter_by(email=email).first():
        return jsonify(error="Email already exists."), 409

    try:
        department_id = int(data["department_id"])
        department = db.session.get(Department, department_id)

        salary = Decimal(str(data["salary"]))
        joining_date = date.fromisoformat(str(data["joining_date"]))

        if department is None:
            return jsonify(error="Department not found."), 400

        if not salary.is_finite() or salary < 0 or salary > Decimal("9999999999.99"):
            return jsonify(error="Invalid salary."), 400

        if joining_date > date.today():
            return jsonify(error="Joining date cannot be in the future."), 400

    except (ValueError, TypeError, InvalidOperation):
        return jsonify(error="Invalid department, salary, or date."), 400

    employee = Employee(
        name=name,
        email=email,
        job_title=job_title,
        department_id=department.id,
        salary=salary,
        joining_date=joining_date,
    )

    db.session.add(employee)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(error="Could not create employee."), 500

    return jsonify(employee_json(employee)), 201


@api_bp.patch("/employees/<int:employee_id>")
@login_required
def update_employee(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify(error="A non-empty JSON object is required."), 400

    if "name" in data:
        name = str(data["name"]).strip()
        if not name or len(name) > 120:
            return jsonify(error="Invalid name."), 400
        employee.name = name

    if "email" in data:
        email = str(data["email"]).strip().lower()
        if not email or len(email) > 150 or "@" not in email:
            return jsonify(error="Invalid email."), 400
        existing = Employee.query.filter_by(email=email).first()
        if existing and existing.id != employee.id:
            return jsonify(error="Email already exists."), 409
        employee.email = email

    if "job_title" in data:
        title = str(data["job_title"]).strip()
        if not title or len(title) > 100:
            return jsonify(error="Invalid job title."), 400
        employee.job_title = title

    if "department_id" in data:
        department = db.session.get(Department, data["department_id"])
        if department is None:
            return jsonify(error="Department not found."), 400
        employee.department_id = department.id

    if "salary" in data:
        try:
            salary = Decimal(str(data["salary"]))
            if not salary.is_finite() or salary < 0 or salary > Decimal("9999999999.99"):
                raise InvalidOperation
            employee.salary = salary
        except (InvalidOperation, ValueError):
            return jsonify(error="Invalid salary."), 400

    if "joining_date" in data:
        try:
            joining_date = date.fromisoformat(str(data["joining_date"]))
            if joining_date > date.today():
                return jsonify(error="Joining date cannot be in the future."), 400
            employee.joining_date = joining_date
        except ValueError:
            return jsonify(error="Invalid joining date."), 400

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify(error="is_active must be true or false."), 400
        employee.is_active = data["is_active"]

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(error="Could not update employee."), 500

    return jsonify(employee_json(employee))


@api_bp.delete("/employees/<int:employee_id>")
@login_required
def deactivate_employee_api(employee_id):
    employee = db.get_or_404(Employee, employee_id)
    employee.is_active = False
    db.session.commit()
    return jsonify(message="Employee deactivated.")

