from flask import Flask
from extensions import db
import os

def create_app(test_config=None):
    """Build and configure the Flask application (application factory).

    Purpose:
        Construct a fully wired Flask app: configure the SQLite database, bind
        the shared SQLAlchemy ``db`` instance, register the bookings and rooms
        blueprints, expose ``/health``, and create any missing tables. Using a
        factory keeps global state out of import time and makes testing easy.

    Args:
        test_config (dict, optional): Config overrides applied on top of the
            defaults before the database is bound. Tests pass this to swap in
            an in-memory SQLite database, e.g.
            ``{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}``.
            Defaults to None (production/dev file-backed database).

    Returns:
        flask.Flask: A ready-to-serve application instance with all routes
            registered and the database initialised.

    Examples:
        Example 1 - run the development server:
            >>> app = create_app()
            >>> app.run(debug=True)  # doctest: +SKIP

        Example 2 - build a test app on an in-memory database:
            >>> app = create_app({"TESTING": True,
            ...                   "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
            >>> app.test_client().get("/health").status_code
            200

    Browser / cURL:
        Not an HTTP endpoint - this is the Python entry point that builds the
        server. Start the server with ``python app.py`` (or
        ``flask --app app run``), then reach its routes in a browser or with
        cURL, e.g. ``curl http://localhost:5000/health``.
    """
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'db', 'bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'workshop-secret-key'
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from routes.bookings import bookings_bp
    from routes.rooms import rooms_bp
    app.register_blueprint(bookings_bp)
    app.register_blueprint(rooms_bp)

    @app.route('/health')
    def health():
        """Report that the service is up (health check).

        Purpose:
            Lightweight liveness probe for load balancers, uptime monitors, or
            a quick manual "is it running?" check. Touches no database.

        Args:
            None: This route takes no path or query parameters.

        Returns:
            dict: ``{"status": "ok", "service": "conference-room-booking"}``,
                serialized by Flask to JSON with HTTP 200.

        Examples:
            Example 1 - from Python (requests):
                >>> import requests
                >>> requests.get("http://localhost:5000/health").json()["status"]
                'ok'

            Example 2 - from the test client:
                >>> app.test_client().get("/health").get_json()["service"]
                'conference-room-booking'

        Browser:
            http://localhost:5000/health

        cURL:
            curl http://localhost:5000/health
        """
        return {'status': 'ok', 'service': 'conference-room-booking'}

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
