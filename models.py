from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
import re


class UserCreate(BaseModel):
    """Модель для создания пользователя (Задание 3.1)"""
    name: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email пользователя")
    age: Optional[int] = Field(None, ge=1, le=150, description="Возраст (опционально)")
    is_subscribed: Optional[bool] = Field(False, description="Подписка на рассылку")
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Имя не может быть пустым')
        return v.strip()


class LoginRequest(BaseModel):
    """Модель для запроса логина"""
    username: str
    password: str


class UserProfile(BaseModel):
    """Модель профиля пользователя"""
    user_id: str
    username: str
    email: str