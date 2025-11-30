import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv

load_dotenv() # Load biến môi trường từ file .env

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "test@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "testtesttesttest"),
    MAIL_FROM=os.getenv("MAIL_FROM", "test@gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_verification_email(email: str, token: str):
    # Lấy domain từ biến môi trường
    domain = os.getenv("DOMAIN", "http://127.0.0.1:8000")
    
    # Tạo link kích hoạt
    url = f"{domain}/verify-email?token={token}"

    html = f"""
    <h3>Xác thực tài khoản</h3>
    <p>Cảm ơn bạn đã đăng ký. Vui lòng click vào link bên dưới để kích hoạt tài khoản:</p>
    <p>{url}</p>
    <br>
    <p>Link này sẽ hết hạn sau 30 phút.</p>
    """

    message = MessageSchema(
        subject="Kích hoạt tài khoản của bạn",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)