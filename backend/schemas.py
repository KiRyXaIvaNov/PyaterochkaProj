from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MessageRequest(BaseModel):
    email: EmailStr
    message: str


class TicketCreateRequest(BaseModel):
    email: EmailStr
    category: str
    message: str
    confidence: Optional[float] = None


class TicketReplyRequest(BaseModel):
    reply: str