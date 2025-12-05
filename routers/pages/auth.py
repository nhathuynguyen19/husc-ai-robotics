from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
import models
import helpers.security as security
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from helpers.security import verify_and_reset_password

BASE_DIR = Path(__file__).resolve().parent.parent.parent

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/signin/", response_class=HTMLResponse)
def page_signin(request: Request, user: models.User | None = Depends(security.get_user_from_cookie)):
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("/pages/signin.html", {"request": request})

@router.get("/signout/", response_class=HTMLResponse)
def page_signin(request: Request, user: models.User | None = Depends(security.get_user_from_cookie)):
    if user:
        return RedirectResponse(url="/auth/signin", status_code=302)
    return templates.TemplateResponse("/pages/signin.html", {"request": request})

@router.get("/forgot_password")
async def get_forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "pages/auth/forgot_password.html",
        {
            "request": request,
        }
    )

@router.get("/reset_password")
async def get_reset_password_page(request: Request, token: str):
    email = verify_reset_password_token(token)
    if not email:
        return HTMLResponse("Token không hợp lệ hoặc đã hết hạn.")

    return templates.TemplateResponse("pages/auth/reset_password.html", {
        "request": request,
        "email": email,
        "token": token
    })
