from fastapi import APIRouter, HTTPException, Request
from ..database import supabase
from ..schemas import UserRegister, UserLogin
from fastapi import Depends

router = APIRouter(prefix="/auth")

@router.post("/register")
async def register(user: UserRegister):
    try:
        # 1. Регистрация в Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {  # Доп. данные (попадут в auth.users.raw_user_meta_data)
                    "username": user.username,
                    "first_name": user.first_name
                }
            }
        })
        
        # 2. Создание профиля в public.profiles
        supabase.table("profiles").insert({
            "user_id": auth_response.user.id,
            "username": user.username,
            "first_name": user.first_name,
            "birth_date": user.birth_date.isoformat(),
            # Базовая ава для всех новых
            "avatar_url": "https://sun9-11.userapi.com/impg/tPC_WVw9-lSqlypnpBxySZm9eloqJBL9di2tSQ/j6onL53z90o.jpg?size=456x492&quality=95&sign=49455024b494d4189109706212579dfe&type=album",
        }).execute()
        
        return {"user_id": auth_response.user.id}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(user: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })

        profile = supabase.table("profiles") \
            .select("*") \
            .eq("user_id", response.user.id) \
            .single() \
            .execute()

        return {
            "access_token": response.session.access_token,
            "user_id": profile.data.get("user_id"),
            "username": profile.data.get("username"),
            "avatar_url": profile.data.get("avatar_url"),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

async def get_current_user(request: Request):
    # Извлекаем токен из заголовка
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    try:
        # Проверяем токен через Supabase
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me")
async def get_profile(user = Depends(get_current_user)):
    profile = supabase.table("profiles") \
        .select("*") \
        .eq("user_id", user.user.id) \
        .single() \
        .execute()
    
    return profile.data