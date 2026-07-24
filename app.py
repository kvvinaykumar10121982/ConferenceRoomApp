from flask import Flask
from extensions import db
import os

def create_app():
    app = Flask(__name__)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'db', 'bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'workshop-secret-key'

    db.init_app(app)

    from routes.bookings import bookings_bp
    from routes.rooms import rooms_bp
    app.register_blueprint(bookings_bp)
    app.register_blueprint(rooms_bp)

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'conference-room-booking'}

    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
