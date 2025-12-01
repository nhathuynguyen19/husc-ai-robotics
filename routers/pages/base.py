from fastapi import APIRouter, Request, Depends, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
import models
import helpers.security as security
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent.parent

router = APIRouter(
    prefix="",
    tags=["pages"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
async def root(
    request: Request, 
    user: models.User | None = Depends(security.get_user_from_cookie)
):
    if user:
        return templates.TemplateResponse("/pages/dashboard.html", {
            "request": request, 
            "user": user
            })
    
    return RedirectResponse(url="/auth/signin", status_code=status.HTTP_302_FOUND)

@router.get("/events", response_class=HTMLResponse)
def get_events(request: Request, 
             tab: str = Query("upcoming", enum=["upcoming", "ongoing", "finished"]),
             user: models.User | None = Depends(security.get_user_from_cookie)
):
    if user:
        return templates.TemplateResponse("/base.html", {
            "request": request, 
            "user": user,
            "tab": tab
            })
    return RedirectResponse(url="/auth/signin", status_code=302)