from sqlalchemy import Boolean, Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base
import enum

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    status = Column(Boolean, default=False) # True: Active
    role = Column(String, default='user')  # 'user', 'admin'
    name_bank = Column(String, nullable=True)
    bank_number = Column(String, nullable=True)

    # Quan hệ ngược lại bảng user_event
    events = relationship("UserEvent", back_populates="user")

class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    day_start = Column(Date, nullable=False)
    from_time = Column(Integer, nullable=False) # Ví dụ: 800 (8:00 AM) hoặc phút
    to_time = Column(Integer, nullable=False)
    number_of_student = Column(Integer, default=0)
    status = Column(String, default="upcoming") # upcoming, ongoing, finished
    school_name = Column(String, nullable=True)

    # Quan hệ ngược lại bảng user_event
    participants = relationship("UserEvent", back_populates="event")
    
class EventRole(str, enum.Enum):
    INSTRUCTOR = "instructor"   # Giảng viên/Người hướng dẫn
    TA = "ta"                   # Trợ giảng

class UserEvent(Base):
    __tablename__ = "user_event"

    # Composite Primary Key (user_id + event_id)
    event_id = Column(Integer, ForeignKey("events.event_id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    
    role = Column(String, default=EventRole.TA) # Role trong sự kiện: participant, staff...
    check_image = Column(Text, nullable=True)    # CLOB trong SQLite map là Text

    user = relationship("User", back_populates="events")
    event = relationship("Event", back_populates="participants")