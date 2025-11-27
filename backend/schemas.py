from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import date

# --- ENUMS & SHARED ---
class RoleEnum:
    ADMIN = "admin"
    USER = "user"

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^0\d{9}$") # Regex: Bắt đầu bằng 0, 10 số
    status: bool = True
    role: str = RoleEnum.USER
    name_bank: Optional[str] = None
    bank_number: Optional[str] = None

    @field_validator('role')
    def role_must_be_valid(cls, v):
        if v not in [RoleEnum.USER, RoleEnum.ADMIN]:
            raise ValueError('Role must be user or admin')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    user_id: int
    
    class Config:
        from_attributes = True
        
# 1. Thêm Schema mới chuyên dùng cho Đăng ký
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    
    @field_validator('email')
    @classmethod
    def validate_gmail(cls, v: str):
        if not v.endswith("@gmail.com"):
            raise ValueError("Hệ thống chỉ chấp nhận tài khoản Gmail (@gmail.com)")
        return v

# --- EVENT SCHEMAS ---
class EventBase(BaseModel):
    name: str
    day_start: date
    from_time: int = Field(..., ge=0, le=2400) # Giả sử format HHMM (0 -> 2400)
    to_time: int = Field(..., ge=0, le=2400)
    number_of_student: int = Field(0, ge=0)
    status: str = "upcoming"
    school_name: Optional[str] = None

    # Validate logic: Giờ kết thúc phải sau giờ bắt đầu
    @model_validator(mode='after')
    def check_time_logic(self):
        if self.to_time <= self.from_time:
            raise ValueError('to_time must be greater than from_time')
        return self

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    event_id: int
    class Config:
        from_attributes = True

# --- USER_EVENT (Tham gia sự kiện) ---
class UserEventLink(BaseModel):
    user_id: int
    role: str = "participant"
    check_image: Optional[str] = None

# --- TOKEN ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None # Đổi từ username sang email