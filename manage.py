from flask.cli import FlaskGroup
from app import create_app
from backend.extensions import db

# create app using factory pattern
app = create_app()

# attach Flask CLI group
cli = FlaskGroup(app)

if __name__ == "__main__":
    cli()
