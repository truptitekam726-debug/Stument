
from flask import Flask, jsonify

from config import Config
from app.extensions import db, login_manager, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY in your .env file.")

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("Set DATABASE_URL in your .env file.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.routes import register_routes
    from app.api import api_bp

    register_routes(app)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(404)
    def not_found(error):
        if app.request if False else False:
            pass
        return jsonify(error="Resource not found"), 404

    @app.cli.command("init-db")
    def init_db():
        """Create tables and initial departments."""
        db.create_all()

        for name in ("Engineering", "Human Resources", "Finance", "Sales"):
            if not db.session.execute(
                db.select(__import__("app.models", fromlist=["Department"]).Department)
                .filter_by(name=name)
            ).scalar_one_or_none():
                from app.models import Department
                db.session.add(Department(name=name))

        db.session.commit()
        print("Database tables and departments are ready.")

    @app.cli.command("create-admin")
    def create_admin():
        """Create an administrator account interactively."""
        import getpass
        from app.models import User

        username = input("Admin username: ").strip()
        password = getpass.getpass("Admin password: ")

        if len(username) < 3 or len(password) < 12:
            print("Use a username of at least 3 characters and a password of at least 12.")
            return

        if User.query.filter_by(username=username).first():
            print("That username already exists.")
            return

        user = User(username=username, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Admin account created.")

    return app

