from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
import models
import helpers.security as security
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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