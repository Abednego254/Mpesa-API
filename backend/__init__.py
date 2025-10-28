import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .extensions import db, migrate, mail
from .routes import items_bp, invoices_bp
from .routes.user_routes import user_bp
from .routes.mpesa_stkpush_routes import mpesa_stk_bp
from .routes.mpesa_callback_routes import mpesa_callback_bp
from .routes.admin_routes import admin_bp
from .routes.commissions import commission_bp
from .routes.auth_routes import auth_bp
from . import models

# Load environment variables
load_dotenv()

jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    # -----------------------------
    # Database Config
    # -----------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:Ciumbe%40254@localhost/myapp_db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -----------------------------
    # JWT Config
    # -----------------------------
    app.config["JWT_SECRET_KEY"] = "super_secret_key_change_this"

    # -----------------------------
    # Mail Config
    # -----------------------------
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = "abednegokaume@gmail.com"
    app.config["MAIL_PASSWORD"] = "rkzy glfu zuql smmm"  # App password
    MAIL_DEFAULT_SENDER = 'abednegokaume@gmail.com'

    # -----------------------------
    # Initialize extensions
    # -----------------------------
    jwt.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)  # ✅ VERY IMPORTANT

    # -----------------------------
    # Register blueprints
    # -----------------------------
    app.register_blueprint(items_bp, url_prefix="/api/items")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(mpesa_stk_bp, url_prefix="/api/mpesa")
    app.register_blueprint(mpesa_callback_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(commission_bp, url_prefix="/api/commissions")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    # -----------------------------
    # Test route
    # -----------------------------
    @app.route("/api/hello")
    def hello():
        return {"message": "Hello from Flask backend!"}

    return app
