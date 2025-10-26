from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
# extensions.py
from flask_mail import Mail

mail = Mail()
db = SQLAlchemy()
migrate = Migrate()

