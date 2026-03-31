import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, status, Request, Response, Cookie, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr, field_validator, ValidationError
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

app = FastAPI(title="Server Applications Development Control Work")

# ========== Задание 3.1 ==========
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: Optional[int] = Field(None, ge=1, le=150)
    is_subscribed: Optional[bool] = False

@app.post("/create_user", status_code=status.HTTP_200_OK)
async def create_user(user: UserCreate):
    """
    Создание пользователя. Принимает JSON с данными пользователя и возвращает их.
    """
    return user.model_dump()

# ========== Задание 3.2 ==========
# Пример данных продуктов
products_db = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99},
]

@app.get("/product/{product_id}")
async def get_product(product_id: int):
    """
    Получение информации о продукте по ID.
    """
    for product in products_db:
        if product["product_id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/products/search")
async def search_products(
    keyword: str,
    category: Optional[str] = None,
    limit: int = 10
):
    """
    Поиск продуктов по ключевому слову и категории.
    """
    results = []
    for product in products_db:
        # Фильтрация по ключевому слову (регистронезависимо)
        if keyword.lower() in product["name"].lower():
            # Фильтрация по категории
            if category is None or product["category"].lower() == category.lower():
                results.append(product)
    # Ограничение количества результатов
    return results[:limit]

# ========== Задание 5.1 (Базовая аутентификация через cookie) ==========
# Хранилище сессий (в реальном приложении использовать Redis или БД)
sessions_db = {}
# Хранилище пользователей
users_db = {
    "user123": {"username": "user123", "password": "password123", "name": "John Doe", "email": "john@example.com"}
}

@app.post("/login")
async def login(response: Response, username: str, password: str):
    """
    Аутентификация пользователя. При успешном входе устанавливает cookie session_token.
    """
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Генерация уникального токена сессии
    session_token = str(uuid.uuid4())
    sessions_db[session_token] = user["username"]
    
    # Установка cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=3600,  # 1 час для простоты
        secure=False   # Для тестирования (в продакшене True)
    )
    return {"message": "Login successful"}

@app.get("/user")
async def get_user_profile(session_token: Optional[str] = Cookie(None)):
    """
    Защищенный маршрут. Возвращает профиль пользователя при наличии валидной сессии.
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    username = sessions_db.get(session_token)
    if not username:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = users_db.get(username)
    return {
        "username": username,
        "name": user["name"],
        "email": user["email"]
    }

# ========== Задание 5.2 (Подписанные cookie с itsdangerous) ==========
# Секретный ключ для подписи (в реальном приложении хранить в переменных окружения)
SECRET_KEY = "my-secret-key-for-signing-cookies-2025"
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Дополнительное хранилище пользователей для этого задания
users_db_signed = {
    "user123": {"username": "user123", "password": "password123", "name": "Alice Smith", "email": "alice@example.com"}
}

@app.post("/login_v2")
async def login_signed(response: Response, username: str, password: str):
    """
    Аутентификация с использованием подписанных cookie.
    """
    user = users_db_signed.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Генерация UUID для user_id
    user_id = str(uuid.uuid4())
    # Создание подписанного токена
    signed_token = serializer.dumps(user_id)
    
    # Установка cookie с подписанным значением
    response.set_cookie(
        key="session_token",
        value=signed_token,
        httponly=True,
        max_age=3600,
        secure=False
    )
    return {"message": "Login successful", "user_id": user_id}

@app.get("/profile")
async def get_profile(session_token: Optional[str] = Cookie(None)):
    """
    Защищенный маршрут с проверкой подписи cookie.
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Расшифровка и проверка подписи
        user_id = serializer.loads(session_token, max_age=3600)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # В реальном приложении здесь будет поиск пользователя по user_id
    return {
        "user_id": user_id,
        "message": "Profile accessed successfully",
        "name": "Alice Smith",
        "email": "alice@example.com"
    }

# ========== Задание 5.3 (Динамическое продление сессии) ==========
# Хранилище сессий с временем последней активности
sessions_with_time_db = {}
# Хранилище пользователей
users_db_extended = {
    "user123": {"username": "user123", "password": "password123", "name": "Bob Johnson", "email": "bob@example.com"}
}

class SessionData:
    def __init__(self, user_id: str, last_activity: float):
        self.user_id = user_id
        self.last_activity = last_activity

@app.post("/login_v3")
async def login_extended(response: Response, username: str, password: str):
    """
    Аутентификация с динамическим временем жизни сессии.
    """
    user = users_db_extended.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = str(uuid.uuid4())
    current_time = time.time()
    
    # Формирование значения cookie: user_id.timestamp
    timestamp_str = str(int(current_time))
    cookie_value = f"{user_id}.{timestamp_str}"
    
    # Создание подписи
    signed_value = serializer.dumps(cookie_value)
    
    # Сохранение данных сессии
    sessions_with_time_db[user_id] = SessionData(user_id, current_time)
    
    # Установка cookie с подписью
    response.set_cookie(
        key="session_token",
        value=signed_value,
        httponly=True,
        max_age=300,  # 5 минут
        secure=False
    )
    return {"message": "Login successful"}

def verify_and_update_session(session_token: str, response: Response) -> dict:
    """
    Проверка сессии и при необходимости обновление времени.
    Возвращает данные пользователя или вызывает исключение.
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Session expired")
    
    try:
        # Проверка подписи
        cookie_value = serializer.loads(session_token, max_age=300)
        parts = cookie_value.split('.')
        if len(parts) != 2:
            raise BadSignature("Invalid format")
        
        user_id = parts[0]
        cookie_timestamp = float(parts[1])
    except (BadSignature, SignatureExpired, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Проверка наличия сессии в хранилище
    session = sessions_with_time_db.get(user_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    current_time = time.time()
    time_since_last_activity = current_time - session.last_activity
    
    # Проверка, не истекла ли сессия (более 5 минут без активности)
    if time_since_last_activity > 300:
        # Удаляем просроченную сессию
        sessions_with_time_db.pop(user_id, None)
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Проверка соответствия времени в cookie серверному времени
    # Допускаем небольшую погрешность (5 секунд)
    if abs(cookie_timestamp - session.last_activity) > 5:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Обновление сессии, если прошло 3-5 минут
    should_update = False
    if time_since_last_activity >= 180 and time_since_last_activity <= 300:
        should_update = True
        new_last_activity = current_time
        session.last_activity = new_last_activity
        
        # Обновляем cookie
        new_timestamp = str(int(new_last_activity))
        new_cookie_value = f"{user_id}.{new_timestamp}"
        new_signed_value = serializer.dumps(new_cookie_value)
        response.set_cookie(
            key="session_token",
            value=new_signed_value,
            httponly=True,
            max_age=300,
            secure=False
        )
    
    # Возвращаем данные пользователя
    user = users_db_extended.get("user123")  # В реальном приложении ищем по user_id
    return {
        "user_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "last_activity": session.last_activity,
        "session_updated": should_update
    }

@app.get("/profile_v3")
async def get_profile_extended(response: Response, session_token: Optional[str] = Cookie(None)):
    """
    Защищенный маршрут с динамическим продлением сессии.
    """
    user_data = verify_and_update_session(session_token, response)
    return user_data

# ========== Задание 5.4 ==========
@app.get("/headers")
async def get_headers(user_agent: Optional[str] = Header(None), accept_language: Optional[str] = Header(None)):
    """
    Возвращает заголовки User-Agent и Accept-Language.
    """
    return {
        "User-Agent": user_agent,
        "Accept-Language": accept_language
    }

# ========== Задание 5.5 (Расширенная работа с заголовками) ==========
from pydantic import BaseModel, field_validator
import re

class CommonHeaders(BaseModel):
    user_agent: str = Field(..., alias="User-Agent")
    accept_language: str = Field(..., alias="Accept-Language")
    
    @field_validator("accept_language")
    @classmethod
    def validate_accept_language(cls, v: str) -> str:
        """
        Валидация формата Accept-Language.
        Пример: en-US,en;q=0.9,es;q=0.8
        """
        if not v:
            return v

        pattern = r'^[a-zA-Z\-*]+(?:;[a-zA-Z\-*]+)?(?:,[a-zA-Z\-*]+(?:;[a-zA-Z\-*]+)?)*$'

        full_pattern = r'^([a-zA-Z]{1,8}(-[a-zA-Z]{1,8})?|\*)(;q=0?\.[0-9]{1,3})?(,([a-zA-Z]{1,8}(-[a-zA-Z]{1,8})?|\*)(;q=0?\.[0-9]{1,3})?)*$'
        
        if not re.match(full_pattern, v):
            raise ValueError(f"Invalid Accept-Language format: {v}")
        return v

@app.get("/headers_v2")
async def get_headers_v2(headers: CommonHeaders = Depends()):
    """
    Возвращает заголовки User-Agent и Accept-Language с использованием модели.
    """
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language
    }

@app.get("/info")
async def get_info(response: Response, headers: CommonHeaders = Depends()):
    """
    Возвращает информацию с заголовками и дополнительным полем message.
    """
    # Добавляем заголовок с текущим серверным временем
    response.headers["X-Server-Time"] = datetime.now().isoformat()
    
    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": headers.user_agent,
            "Accept-Language": headers.accept_language
        }
    }

# ========== Вспомогательные маршруты для тестирования ==========
@app.get("/")
async def root():
    return {
        "message": "Server Applications Development Control Work",
        "endpoints": {
            "3.1": "/create_user (POST)",
            "3.2": "/product/{product_id} (GET), /products/search (GET)",
            "5.1": "/login (POST), /user (GET)",
            "5.2": "/login_v2 (POST), /profile (GET)",
            "5.3": "/login_v3 (POST), /profile_v3 (GET)",
            "5.4": "/headers (GET)",
            "5.5": "/headers_v2 (GET), /info (GET)"
        }
    }

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()}
    )