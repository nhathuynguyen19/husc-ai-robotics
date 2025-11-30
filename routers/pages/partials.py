from fastapi import APIRouter
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
import models, schemas, database
import helpers.security as security
from schemas import EventRole
from datetime import datetime, date, time
from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

PERIOD_END_TIMES = {
    1:  (8, 0),
    2:  (9, 0),
    3:  (10, 0),
    4:  (11, 0),
    5:  (14, 0),
    6:  (15, 0),
    7:  (16, 0),
    8:  (17, 0),
    9:  (18, 25),
    10: (19, 25),
    11: (20, 25),
    12: (21, 25),
}


# Hàm helper chuyển tiết học sang giờ (7h - 13h) để dùng trong template
def format_period(period: int) -> str:
    hour = 7 + (period - 1) if period <= 6 else 13 + (period - 7)
    return f"{hour}h00"

router = APIRouter(
    prefix="/partials",
    tags=["partials"],
)

@router.get("/events-table")
async def render_events_table(
    request: Request,
    db: Session = Depends(database.get_db), 
    current_user = Depends(security.get_user_from_cookie)
):
    if not current_user:
        return templates.TemplateResponse(
            "partials/events_table.html", 
            {"request": request, "events": [], "error": "Vui lòng đăng nhập để xem lịch."}
        )

   # Lấy sự kiện chưa bị xóa
    events = db.query(models.Event)\
        .filter(models.Event.status != "deleted")\
        .options(joinedload(models.Event.participants).joinedload(models.UserEvent.user))\
        .order_by(models.Event.day_start)\
        .limit(20)\
        .all()

    events_view = []
    now = datetime.now()

    for event in events:
        # 1. Lọc danh sách Instructor và TA để hiển thị text
        instructors = [p.user.full_name for p in event.participants if p.role == 'instructor' and p.user]
        tas = [p.user.full_name for p in event.participants if p.role == 'ta' and p.user]
        
        # 2. Kiểm tra trạng thái của User hiện tại với Event này
        # Tìm xem user có trong list participants không
        current_participant = next((p for p in event.participants if p.user_id == current_user.user_id), None)
        
        is_joined = current_participant is not None
        user_role = current_participant.role if is_joined else None
        attendance_status = current_participant.status if is_joined else None # 'registered', 'attended'

        # 3. Logic thời gian để enable/disable nút "Hoàn thành"
        # Tính thời gian kết thúc sự kiện
        end_hour, end_minute = PERIOD_END_TIMES.get(event.end_period, (23, 59))
        event_end_time = datetime.combine(event.day_start, time(hour=end_hour, minute=end_minute))
        is_ended = now > event_end_time

        # 4. Kiểm tra xem sự kiện đã đầy chưa (để disable nút đăng ký)
        current_count = len(event.participants)
        is_full = current_count >= event.max_user_joined

        events_view.append({
            "event_id": event.event_id,
            "day_str": event.day_start.strftime("%d/%m/%Y"), # Format ngày
            "time_str": f"{format_period(event.start_period)} - {format_period(event.end_period + 1)}",
            "period_detail": f"(Tiết {event.start_period}-{event.end_period})",
            "school_name": event.school_name,
            "name": event.name,
            "student_count": event.number_of_student,
            "instructors": ", ".join(instructors) if instructors else "---",
            "tas": ", ".join(tas) if tas else "---",
            
            # Các biến flag cho UI
            "is_joined": is_joined,           # Đã tham gia chưa
            "user_role": user_role,           # Vai trò: instructor/ta
            "attendance_status": attendance_status, # registered/attended
            "is_ended": is_ended,             # Sự kiện đã kết thúc về mặt thời gian chưa
            "is_full": is_full,               # Đã full slot chưa
            "is_locked": event.is_locked,
            "status": event.status
        })

    return templates.TemplateResponse(
        "partials/events_table.html", 
        {
            "request": request, 
            "events": events_view,
            "user": current_user
        }
    )