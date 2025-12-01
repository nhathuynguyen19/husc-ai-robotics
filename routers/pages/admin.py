# husc-ai-robotics/routers/pages/admin.py

from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Annotated, Optional

import database
import models
import schemas
import helpers.security as security

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/admin",
    tags=["pages_admin"]
)

# 1. GET: Hiển thị form tạo tài khoản
@router.get("/users/create")
async def get_create_user_page(
    request: Request,
    current_user: models.User = Depends(security.get_current_admin_from_cookie)
):
    # Nếu dependency trả về RedirectResponse (chưa login hoặc không phải admin), return luôn
    if isinstance(current_user, RedirectResponse):
        return current_user
        
    return templates.TemplateResponse(
        "pages/admin/create_user.html",
        {
            "request": request,
            "user": current_user,
            "error": None,
            "success": None
        }
    )

@router.post("/users/create")
async def create_user_action(
    request: Request,
    email: Annotated[str, Form()],
    role: Annotated[str, Form()],
    # Cập nhật: Cho phép None hoặc chuỗi rỗng
    full_name: Annotated[Optional[str], Form()] = None, 
    phone: Annotated[Optional[str], Form()] = None,
    # Cập nhật: Mặc định là husc1234 nếu form không gửi lên (dù form html đã có value sẵn)
    password: Annotated[str, Form()] = "husc1234", 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_admin_from_cookie)
):
    # Logic xử lý chuỗi rỗng thành None để lưu vào DB sạch hơn
    if full_name == "": full_name = None
    if phone == "": phone = None

    try:
        # Validate dữ liệu
        user_data = schemas.UserCreateAdmin(
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            phone=phone,
            status=True
        )
        
        # Check email trùng
        if db.query(models.User).filter(models.User.email == user_data.email).first():
            raise ValueError("Email này đã được sử dụng.")

        # Tạo User
        new_user = models.User(
            email=user_data.email,
            hashed_password=security.get_password_hash(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=user_data.role,
            status=user_data.status
        )
        db.add(new_user)
        db.commit()
        
        return templates.TemplateResponse(
            "pages/admin/create_user.html",
            {
                "request": request,
                "user": current_user,
                "success": f"Đã tạo tài khoản {user_data.email} thành công!",
                "form_data": None # Reset form sau khi thành công
            }
        )

    except Exception as e:
        db.rollback()
        # Xử lý thông báo lỗi hiển thị cho đẹp
        error_msg = str(e).replace("Value error, ", "")
        return templates.TemplateResponse(
            "pages/admin/create_user.html",
            {
                "request": request,
                "user": current_user,
                "error": error_msg,
                "form_data": { # Giữ lại dữ liệu cũ khi lỗi
                    "email": email,
                    "full_name": full_name,
                    "phone": phone,
                    "role": role
                }
            }
        )