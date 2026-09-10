from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class MessageRequest(BaseModel):
    email: EmailStr
    message: str
