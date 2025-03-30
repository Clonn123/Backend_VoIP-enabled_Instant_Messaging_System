from fastapi import APIRouter, HTTPException
from ..database import supabase
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

@router.post("/register")
async def register_user(user: UserRegister):
    try:
        # 1. Регистрация в Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        
        # 2. Сохранение username в таблице profiles
        supabase.table("profiles").insert({
            "user_id": auth_response.user.id,
            "username": user.username
        }).execute()
        
        return {
            "message": "User created",
            "user_id": auth_response.user.id,
            "username": user.username
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))