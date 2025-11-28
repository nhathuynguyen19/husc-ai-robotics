from typing import Annotated
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_redoc_html
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy.orm import Session
from jose import jwt, JWTError

from backend import models, schemas, auth, database
from backend.models import EventRole
from backend.email_utils import send_verification_email


# ============================
# PATH & TEMPLATE CONFIG
# ============================

BASE_DIR = Path(__file__).resolve().parent.parent  # husc-ai-robotics/

app = FastAPI(docs_url="/docs", redoc_url=None)

# Session (bắt buộc nếu bạn dùng session để lưu token)
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# Trỏ templates → app/templates
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Trỏ static → app/static
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Tạo bảng DB
models.Base.metadata.create_all(bind=database.engine)


# ============================
# CUSTOM REDOC
# ============================
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


# ============================
# AUTH HTML PAGES
# ============================

@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def page_register(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
def page_forgot_password(request: Request):
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})


# ============================
# AUTH API (LOGIN – REGISTER – RESET)
# ============================

@app.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(database.get_db)
):
    # 1. Tìm user theo Email
    # Mặc dù biến tên là form_data.username (do chuẩn OAuth2 bắt buộc), 
    # nhưng người dùng sẽ nhập Email vào đây.
    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    # 2. Kiểm tra user có tồn tại và mật khẩu đúng không
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. (MỚI) Kiểm tra đã kích hoạt tài khoản chưa
    if not user.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not active. Please check your email to verify.",
        )

    # 4. Tạo Token
    access_token = auth.create_access_token(
        data={"sub": user.email}, # Lưu email vào trong token
        expires_delta=auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.UserResponse)
async def create_user(
    user: schemas.UserRegister, 
    background_tasks: BackgroundTasks, # Sử dụng BackgroundTasks để gửi mail ko bị lag
    db: Session = Depends(database.get_db)
):
    # Check email tồn tại
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    
    # Tạo user với status mặc định là False (do config trong model)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        status=False  # Đảm bảo status là False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Tạo token kích hoạt (có thể dùng chung hàm tạo token nhưng set thời gian ngắn hơn)
    # Token này chứa email của user để khi verify ta biết là ai
    verification_token = auth.create_access_token(
        data={"sub": new_user.email}, 
        expires_delta=auth.timedelta(minutes=30) # Link sống 30 phút
    )
    
    # Gửi mail trong nền (Background Task)
    background_tasks.add_task(send_verification_email, new_user.email, verification_token)
    
    return new_user


@app.post("/forgot-password")
def forgot_password(email: str = Form(...), request: Request = None):
    """Demo UI, không gửi mail thật."""
    return templates.TemplateResponse(
        "partials/success.html",
        {"request": request, "message": f"Đã gửi hướng dẫn đặt lại mật khẩu đến {email}"},
    )


@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email(request: Request, token: str, db: Session = Depends(database.get_db)):
    """Xác thực email."""
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
    except:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "Token hết hạn hoặc không hợp lệ"},
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "message": "User không tồn tại"},
        )

    if user.status:
        return templates.TemplateResponse(
            "partials/success.html",
            {"request": request, "message": "Tài khoản đã được kích hoạt trước đó"},
        )

    user.status = True
    db.commit()

    return templates.TemplateResponse(
        "partials/success.html",
        {"request": request, "message": "Kích hoạt thành công – bạn có thể đăng nhập"},
    )


# ============================
# USER PAGES (HTML)
# ============================

@app.get("/events", response_class=HTMLResponse)
def page_events(request: Request):
    return templates.TemplateResponse("user/events.html", {"request": request})


# ============================
# ADMIN PAGES (HTML)
# ============================

@app.get("/admin/events", response_class=HTMLResponse)
def admin_events_page(request: Request):
    return templates.TemplateResponse("admin/events.html", {"request": request})


# ============================
# BACKEND API (EVENT CRUD)
# ============================

@app.get("/api/events", response_model=list[schemas.EventResponse])
def get_events_api(
    db: Session = Depends(database.get_db),
    current_user=Depends(auth.get_current_user)
):
    return db.query(models.Event).all()


@app.post("/api/events")
def create_event_api(
    event: schemas.EventCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(auth.get_current_admin_user)
):
    new_event = models.Event(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event
