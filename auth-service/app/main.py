from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Временное "хранилище" в памяти
fake_db: List[dict] = []

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

@app.post("/register")
def register_user(user: UserCreate):
    # Проверка на существующего пользователя
    if any(u["username"] == user.username or u["email"] == user.email for u in fake_db):
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Сохраняем "как есть" (без хеширования)
    user_data = user.dict()
    fake_db.append(user_data)
    
    return {"Логин": user.username, "Почта": user.email}  # Возвращаем без пароля