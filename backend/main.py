from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth, database
from email_utils import send_verification_email
from jose import jwt, JWTError

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# --- AUTH ---
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

@app.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Could not validate credentials or token expired",
    )
    
    try:
        # Giải mã token
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Tìm user trong DB
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.status:
        return {"message": "Account already activated"}
    
    # Kích hoạt tài khoản
    user.status = True
    db.commit()
    
    return {"message": "Account activated successfully. You can now login."}

# --- USER ENDPOINTS ---
@app.get("/users/me/", response_model=schemas.UserResponse)
async def read_users_me(current_user: Annotated[models.User, Depends(auth.get_current_user)]):
    return current_user

# --- EVENT ENDPOINTS (Admin Create) ---
@app.post("/events/", response_model=schemas.EventResponse)
def create_event(
    event: schemas.EventCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    new_event = models.Event(**event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event

@app.get("/events/", response_model=list[schemas.EventResponse])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user = Depends(auth.get_current_user)):
    events = db.query(models.Event).offset(skip).limit(limit).all()
    return events

# --- USER-EVENT ACTION (User tham gia sự kiện) ---
@app.post("/events/{event_id}/join")
def join_event(
    event_id: int,
    role: str = "participant", # Query param hoặc body
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # 1. Check event tồn tại
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # 2. Check đã tham gia chưa
    existing_link = db.query(models.UserEvent).filter(
        models.UserEvent.user_id == current_user.user_id,
        models.UserEvent.event_id == event_id
    ).first()
    if existing_link:
        raise HTTPException(status_code=400, detail="User already joined this event")

    # 3. Tạo link
    user_event = models.UserEvent(user_id=current_user.user_id, event_id=event_id, role=role)
    db.add(user_event)
    
    # Optional: Tăng số lượng student
    event.number_of_student += 1
    
    db.commit()
    return {"detail": "Joined event successfully"}