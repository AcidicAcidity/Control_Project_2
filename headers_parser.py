from fastapi import Header, HTTPException
from pydantic import BaseModel, Field, field_validator
import re


class CommonHeaders(BaseModel):
    """
    Модель для парсинга и валидации заголовков (Задание 5.4)
    """
    user_agent: str = Field(..., alias="User-Agent")
    accept_language: str = Field(..., alias="Accept-Language")
    
    @field_validator('accept_language')
    @classmethod
    def validate_accept_language(cls, v: str) -> str:
        """
        Валидация формата Accept-Language
        Пример: en-US,en;q=0.9,es;q=0.8
        """
        if not v or not v.strip():
            raise ValueError('Accept-Language header is required')
        
        # Паттерн для валидации Accept-Language
        # Допускает форматы: "en", "en-US", "en-US,en;q=0.9", etc.
        pattern = r'^[a-zA-Z]{2}(-[a-zA-Z]{2})?(,[a-zA-Z]{2}(-[a-zA-Z]{2})?(;q=[01](\.\d{1,3})?)?)*$'
        
        # Упрощенная валидация - проверяем, что строка не пустая и содержит разумные символы
        if len(v) > 500:  # Слишком длинное значение
            raise ValueError('Accept-Language header is too long')
        
        # Проверяем, что нет опасных символов
        if re.search(r'[<>"\']', v):
            raise ValueError('Accept-Language header contains invalid characters')
        
        return v
    
    class Config:
        # Позволяет использовать оригинальные имена полей
        populate_by_name = True