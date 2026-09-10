from pydantic import BaseModel, EmailStr
from typing import Optional

# Модель для входа в систему (/api/auth/login)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Модель для отправки сообщения (/api/chat/send)
class MessageRequest(BaseModel):
    email: EmailStr
    message: str
