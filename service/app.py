import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from service import db
from service.views import views_bp

logger = logging.getLogger(__name__)
LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def create_app(testing=False):
    """
    Create a Flask app instance,
    sets SQLALCHEMY configurations
    """
    migrate = Migrate()

    app = Flask(__name__)
    app.register_blueprint(views_bp, url_prefix="")

    app.config["LOG_LEVEL"] = "INFO"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

    db.init_app(app)

    migrate.init_app(app, db)

    db.create_all(app=app)
    setup_logging(app)

    return app


def setup_logging(app):
    verbosity = app.config["LOG_LEVEL"]
    global_logger = logging.getLogger("")
    global_logger.setLevel(LOG_LEVEL_MAP[verbosity])
    global_stream = logging.StreamHandler()
    global_stream.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
    ))
    global_logger.addHandler(global_stream)
