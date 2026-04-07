import uuid
import time
from typing import Optional, Tuple, Dict
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime

# Секретный ключ для подписи (в реальном приложении хранить в .env)
SECRET_KEY = "your-super-secret-key-change-in-production-2025"
SALT = "session-signature"
SESSION_MAX_AGE = 300  # 5 минут в секундах
REFRESH_THRESHOLD = 180  # 3 минуты в секундах

# Создаем подписыватель
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Хранилище для пользователей (имитация базы данных)
users_db: Dict[str, dict] = {
    "user123": {
        "username": "user123", 
        "password": "password123", 
        "email": "user@example.com",
        "user_id": "user123"
    },
    "admin": {
        "username": "admin", 
        "password": "admin123", 
        "email": "admin@example.com",
        "user_id": "admin"
    }
}

# Хранилище для активных сессий (user_id -> last_activity)
active_sessions: Dict[str, int] = {}


def generate_user_id() -> str:
    """Генерирует уникальный UUID для пользователя"""
    return str(uuid.uuid4())


def verify_credentials(username: str, password: str) -> Optional[str]:
    """
    Проверяет учетные данные и возвращает user_id
    """
    if username in users_db and users_db[username]["password"] == password:
        return users_db[username]["user_id"]
    return None


def create_session_token(user_id: str, current_time: Optional[int] = None) -> str:
    """
    Создает подписанный session_token в формате:
    <user_id>.<timestamp> (затем подписывается)
    """
    if current_time is None:
        current_time = int(time.time())
    
    # Создаем данные для подписи
    data = f"{user_id}.{current_time}"
    signature = serializer.dumps(data, salt=SALT)
    
    # Обновляем активную сессию
    active_sessions[user_id] = current_time
    
    return signature


def verify_and_decode_session_token(token: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Проверяет подпись и декодирует session_token.
    Возвращает (user_id, timestamp, error_message)
    """
    try:
        # Расшифровываем подпись
        data = serializer.loads(token, salt=SALT, max_age=SESSION_MAX_AGE)
        
        # Разбираем данные
        parts = data.split('.')
        if len(parts) != 2:
            return None, None, "Invalid token format"
        
        user_id = parts[0]
        timestamp = int(parts[1])
        
        # Проверяем, соответствует ли timestamp сохраненному в активной сессии
        if user_id in active_sessions and active_sessions[user_id] != timestamp:
            return None, None, "Session timestamp mismatch"
        
        return user_id, timestamp, None
        
    except SignatureExpired:
        return None, None, "Session expired"
    except BadSignature:
        return None, None, "Invalid signature"
    except Exception as e:
        return None, None, f"Decode error: {str(e)}"


def should_refresh_session(last_activity: int, current_time: int) -> bool:
    """
    Определяет, нужно ли обновить сессию.
    Возвращает True, если прошло более REFRESH_THRESHOLD секунд,
    но менее SESSION_MAX_AGE секунд.
    """
    elapsed = current_time - last_activity
    
    # Если прошло больше 5 минут - сессия мертва
    if elapsed >= SESSION_MAX_AGE:
        return False
    
    # Если прошло больше 3 минут - нужно обновить
    if elapsed >= REFRESH_THRESHOLD:
        return True
    
    return False


def is_session_valid(last_activity: int, current_time: int) -> bool:
    """Проверяет, не истекла ли сессия"""
    elapsed = current_time - last_activity
    return elapsed < SESSION_MAX_AGE


def get_user_profile(user_id: str) -> Optional[dict]:
    """Получает профиль пользователя по ID"""
    if user_id in users_db:
        return {
            "user_id": user_id,
            "username": users_db[user_id]["username"],
            "email": users_db[user_id]["email"]
        }
    return None


def update_session_activity(user_id: str, timestamp: int) -> None:
    """Обновляет время последней активности сессии"""
    active_sessions[user_id] = timestamp


def delete_session(user_id: str) -> None:
    """Удаляет сессию пользователя"""
    if user_id in active_sessions:
        del active_sessions[user_id]