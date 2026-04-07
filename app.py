from fastapi import FastAPI, HTTPException, Request, Response, Depends, Cookie, Query
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
import time
from datetime import datetime

from models import UserCreate, LoginRequest
from products import get_product_by_id, search_products
from session_manager import (
    verify_credentials, 
    create_session_token, 
    verify_and_decode_session_token,
    should_refresh_session, 
    is_session_valid, 
    get_user_profile, 
    SESSION_MAX_AGE,
    update_session_activity
)

app = FastAPI(title="FastAPI Coursework", description="Контрольная работа №2")


# ==================== Задание 3.1 ====================
@app.post("/create_user", response_model=UserCreate)
async def create_user(user: UserCreate):
    """
    Создание пользователя (POST /create_user)
    Принимает JSON с данными пользователя, валидирует и возвращает их
    """
    return user


# ==================== Задание 3.2 ====================
@app.get("/product/{product_id}")
async def get_product(product_id: int):
    """
    Получение информации о продукте по ID (GET /product/{product_id})
    """
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/products/search")
async def search_products_endpoint(
    keyword: str = Query(..., min_length=1, description="Ключевое слово для поиска"),
    category: Optional[str] = Query(None, description="Категория для фильтрации"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество результатов")
):
    """
    Поиск продуктов (GET /products/search)
    Параметры: keyword, category (опц), limit (опц, по умолчанию 10)
    """
    results = search_products(keyword, category, limit)
    return results


# ==================== Задания 5.1, 5.2, 5.3 ====================
@app.post("/login")
async def login(login_data: LoginRequest, response: Response):
    """
    Аутентификация пользователя и установка session_token cookie
    """
    user_id = verify_credentials(login_data.username, login_data.password)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Создаем подписанный токен с текущим временем
    current_timestamp = int(time.time())
    token = create_session_token(user_id, current_timestamp)
    
    # Устанавливаем cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,          # Только для HTTP
        secure=False,           # Для тестирования (в продакшене True)
        max_age=SESSION_MAX_AGE,
        samesite="lax"
    )
    
    return {"message": "Login successful", "user_id": user_id}


@app.get("/profile")
async def get_profile(request: Request, response: Response, session_token: Optional[str] = Cookie(None)):
    """
    Защищенный маршрут с динамическим временем жизни сессии
    """
    # Проверяем наличие cookie
    if not session_token:
        response.status_code = 401
        return {"message": "Unauthorized"}
    
    # Проверяем и декодируем токен
    user_id, timestamp, error = verify_and_decode_session_token(session_token)
    
    if error:
        response.status_code = 401
        if "expired" in error.lower():
            return {"message": "Session expired"}
        elif "signature" in error.lower():
            return {"message": "Invalid session"}
        return {"message": error}
    
    # Проверяем валидность сессии по времени
    current_time = int(time.time())
    
    if not is_session_valid(timestamp, current_time):
        response.status_code = 401
        return {"message": "Session expired"}
    
    # Получаем профиль пользователя
    user_profile = get_user_profile(user_id)
    if not user_profile:
        response.status_code = 401
        return {"message": "User not found"}
    
    # Проверяем, нужно ли обновить сессию
    if should_refresh_session(timestamp, current_time):
        # Обновляем токен с новым временем
        new_token = create_session_token(user_id, current_time)
        response.set_cookie(
            key="session_token",
            value=new_token,
            httponly=True,
            secure=False,
            max_age=SESSION_MAX_AGE,
            samesite="lax"
        )
        update_session_activity(user_id, current_time)
    
    return {
        "message": "Profile retrieved successfully",
        "profile": user_profile,
        "last_activity": datetime.fromtimestamp(timestamp).isoformat(),
        "session_valid_until": datetime.fromtimestamp(timestamp + SESSION_MAX_AGE).isoformat()
    }


@app.get("/user")
async def get_user(session_token: Optional[str] = Cookie(None)):
    """
    Простой защищенный маршрут (для задания 5.1 и 5.2)
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id, timestamp, error = verify_and_decode_session_token(session_token)
    
    if error or not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_profile = get_user_profile(user_id)
    if not user_profile:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return user_profile


@app.post("/logout")
async def logout(response: Response):
    """Выход из системы - удаляем cookie"""
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}


# ==================== Задание 5.4 ====================
from headers_parser import CommonHeaders


@app.get("/headers")
async def get_headers(headers: CommonHeaders = Depends()):
    """
    Возвращает заголовки User-Agent и Accept-Language
    """
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language
    }


@app.get("/info")
async def get_info(request: Request, headers: CommonHeaders = Depends()):
    """
    Возвращает приветственное сообщение и заголовки,
    плюс добавляет X-Server-Time в заголовки ответа
    """
    current_time = datetime.now().isoformat()
    
    return JSONResponse(
        content={
            "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
            "headers": {
                "User-Agent": headers.user_agent,
                "Accept-Language": headers.accept_language
            }
        },
        headers={"X-Server-Time": current_time}
    )


# ==================== Дополнительные эндпоинты для тестирования ====================
@app.get("/")
async def root():
    """Корневой эндпоинт с информацией о доступных маршрутах"""
    return {
        "message": "FastAPI Coursework Server",
        "available_endpoints": {
            "user_creation": "POST /create_user",
            "product_by_id": "GET /product/{product_id}",
            "product_search": "GET /products/search",
            "login": "POST /login",
            "profile": "GET /profile",
            "user": "GET /user",
            "logout": "POST /logout",
            "headers": "GET /headers",
            "info": "GET /info"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)