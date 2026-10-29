
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import (
    render_template, request, redirect, url_for,
    flash, abort
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Employee, Department


def register_routes(app):

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                flash("Welcome back!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid username or password.", "danger")

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        total = Employee.query.filter_by(is_active=True).count()
        departments = Department.query.count()
        inactive = Employee.query.filter_by(is_active=False).count()
        recent = (
            Employee.query
            .filter_by(is_active=True)
            .order_by(Employee.id.desc())
            .limit(5)
            .all()
        )

        return render_template(
            "dashboard.html",
            total=total,
            departments=departments,
            inactive=inactive,
            recent=recent,
        )

    @app.route("/employees")
    @login_required
    def employees():
        search = request.args.get("q", "").strip()

        query = Employee.query.join(Department)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    Employee.name.ilike(pattern),
                    Employee.email.ilike(pattern),
                    Employee.job_title.ilike(pattern),
                    Department.name.ilike(pattern),
                )
            )

        page = request.args.get("page", 1, type=int)
        page = max(page or 1, 1)

        pagination = query.order_by(Employee.id.desc()).paginate(
            page=page, per_page=10, error_out=False
        )

        return render_template(
            "employees.html",
            pagination=pagination,
            search=search,
        )

    @app.route("/employees/new", methods=["GET", "POST"])
    @login_required
    def employee_create():
        return employee_form()

    @app.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
    @login_required
    def employee_edit(employee_id):
        employee = db.get_or_404(Employee, employee_id)
        return employee_form(employee)

    def employee_form(employee=None):
        departments = Department.query.order_by(Department.name).all()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            job_title = request.form.get("job_title", "").strip()
            department_id = request.form.get("department_id", type=int)
            salary_text = request.form.get("salary", "").strip()
            joining_date_text = request.form.get("joining_date", "").strip()

            errors = []

            if not name or len(name) > 120:
                errors.append("Enter a name of up to 120 characters.")

            if not email or len(email) > 150 or "@" not in email:
                errors.append("Enter a valid email address.")

            if not job_title or len(job_title) > 100:
                errors.append("Enter a job title of up to 100 characters.")

            department = db.session.get(Department, department_id)
            if department is None:
                errors.append("Select a valid department.")

            existing = Employee.query.filter_by(email=email).first()
            if existing and (employee is None or existing.id != employee.id):
                errors.append("That email is already assigned to an employee.")

            try:
                salary = Decimal(salary_text)
                if not salary.is_finite() or salary < 0 or salary > Decimal("9999999999.99"):
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                salary = Decimal("0")
                errors.append("Enter a valid non-negative salary.")

            try:
                joining_date = date.fromisoformat(joining_date_text)
                if joining_date > date.today():
                    errors.append("Joining date cannot be in the future.")
            except ValueError:
                joining_date = date.today()
                errors.append("Enter a valid joining date.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "employee_form.html",
                    employee=employee,
                    departments=departments,
                )

            if employee is None:
                employee = Employee()
                db.session.add(employee)

            employee.name = name
            employee.email = email
            employee.job_title = job_title
            employee.department_id = department.id
            employee.salary = salary
            employee.joining_date = joining_date

            try:
                db.session.commit()
                flash("Employee saved successfully.", "success")
                return redirect(url_for("employees"))
            except Exception:
                db.session.rollback()
                app.logger.exception("Failed to save employee")
                flash("Could not save the employee. Check the submitted data.", "danger")

        return render_template(
            "employee_form.html",
            employee=employee,
            departments=departments,
        )

    @app.route("/employees/<int:employee_id>/deactivate", methods=["POST"])
    @login_required
    def employee_deactivate(employee_id):
        employee = db.get_or_404(Employee, employee_id)
        employee.is_active = False
        db.session.commit()
        flash("Employee deactivated.", "success")
        return redirect(url_for("employees"))

