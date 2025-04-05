from fastapi import FastAPI
from .routes.auth import router as auth_router
from .routes.profile import router as profile_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Разрешаем CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5555"],  # Точный адрес фронта
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST, OPTIONS и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

app.include_router(auth_router)
app.include_router(profile_router)