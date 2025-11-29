# from typing import Annotated
from fastapi import FastAPI, Request
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlalchemy.orm import Session, joinedload
import models, schemas, routers.auth as auth, database
# from utils.email_utils import send_verification_email
# from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles # <--- Import cái này
from fastapi.openapi.docs import get_redoc_html # <--- Import cái này
# from models import EventRole
from routers import auth, users, events, admin
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(docs_url="/docs", redoc_url=None)



# Gắn state limiter vào app để dùng trong Router
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(admin.router)

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )
 
