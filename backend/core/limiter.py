# backend/core/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Khởi tạo Limiter ở đây để dùng chung
limiter = Limiter(key_func=get_remote_address)