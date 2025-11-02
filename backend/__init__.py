import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .extensions import db, migrate, mail, socketio
from .routes import items_bp, invoices_bp
from .routes.user_routes import user_bp
from .routes.mpesa_stkpush_routes import mpesa_stk_bp
from .routes.mpesa_callback_routes import mpesa_callback_bp
from .routes.admin_routes import admin_bp
from .routes.commissions import commission_bp
from .routes.auth_routes import auth_bp
from . import models
from .routes.photo_routes import photo_bp
from .routes.sales_routes import sales_bp

# Load environment variables
load_dotenv()

jwt = JWTManager()


def create_app():
    app = Flask(__name__, static_folder="static")
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # -----------------------------
    # Database Configuration
    # -----------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "mysql+pymysql://root:Ciumbe%40254@localhost/myapp_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -----------------------------
    # JWT Configuration
    # -----------------------------
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super_secret_key_change_this")

    # -----------------------------
    # Mail Configuration
    # -----------------------------
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "abednegokaume@gmail.com")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "rkzy glfu zuql smmm")
    app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]

    # -----------------------------
    # Initialize Extensions
    # -----------------------------
    jwt.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # -----------------------------
    # Register Blueprints
    # -----------------------------
    app.register_blueprint(items_bp, url_prefix="/api/items")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(mpesa_stk_bp, url_prefix="/api/mpesa")
    app.register_blueprint(mpesa_callback_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(commission_bp, url_prefix="/api/commissions")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(photo_bp, url_prefix="/api/photo")
    app.register_blueprint(sales_bp, url_prefix="/api/sales")

    # -----------------------------
    # Simple Health Check Route
    # -----------------------------
    @app.route("/api/hello", methods=["GET"])
    def hello():
        return jsonify({"message": "Hello from Flask backend!"})

    # -----------------------------
    # Root Redirect (Optional)
    # -----------------------------
    @app.route("/", methods=["GET"])
    def home():
        return jsonify({"status": "running", "message": "Backend is live!"})

    return app
