from typing import List, Optional

# Пример данных продуктов (Задание 3.2)
sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 599.99},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 19.99},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 1299.99},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 99.99},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 299.99}
]

# Хранилище для имитации базы данных продуктов
products_db = {p["product_id"]: p for p in sample_products}


def get_product_by_id(product_id: int) -> Optional[dict]:
    """Получить продукт по ID"""
    return products_db.get(product_id)


def search_products(keyword: str, category: Optional[str] = None, limit: int = 10) -> List[dict]:
    """Поиск продуктов по ключевому слову и категории"""
    results = []
    keyword_lower = keyword.lower()
    
    for product in products_db.values():
        # Фильтр по ключевому слову
        if keyword_lower not in product["name"].lower():
            continue
        
        # Фильтр по категории
        if category and product["category"].lower() != category.lower():
            continue
        
        results.append(product)
        
        if len(results) >= limit:
            break
    
    return results