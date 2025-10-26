from backend import create_app
from backend.extensions import mail

app = create_app()

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='abednegokaume@gmail.com',
    MAIL_PASSWORD='Ciumbe@254'
)

mail.init_app(app)

if __name__ == "__main__":
    app.run(debug=True)
