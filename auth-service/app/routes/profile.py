from fastapi import APIRouter, Depends, HTTPException, Request
from ..schemas import UpdateUsername, UpdateFirstName, UpdateEmail, UpdatePassword, UpdateAvatar
from ..database import supabase

router = APIRouter(prefix="/profile")

async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.patch("/update_username")
def update_username(data: UpdateUsername, user=Depends(get_current_user)):
    user_id = user.user.id
    
    try:
        check = supabase.table("profiles") \
            .select("user_id") \
            .eq("username", data.username) \
            .execute()
        
        if check.data and any(profile["user_id"] != user_id for profile in check.data):
            raise HTTPException(
                status_code=400,
                detail="Имя пользователя уже используется"
            )
        
        result = supabase.table("profiles") \
            .update({"username": data.username}) \
            .eq("user_id", user_id) \
            .execute()
        
        if hasattr(result, 'error') and result.error:
            raise HTTPException(
                status_code=400,
                detail="Ошибка обновления имени пользователя"
            )
        
        return {"message": "Имя пользователя обновлено"}
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )

@router.patch("/update_first_name")
def update_first_name(data: UpdateFirstName, user=Depends(get_current_user)):
    user_id = user.user.id

    try:
        result = supabase.table("profiles").update({"first_name": data.first_name}) \
            .eq("user_id", user_id).execute()

        if hasattr(result, 'error') and result.error:
            raise HTTPException(status_code=400, detail="Ошибка обновления имени")
        
        return {"message": "Имя обновлено"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.patch("/update_avatar")
def update_avatar(data: UpdateAvatar, user=Depends(get_current_user)):
    user_id = user.user.id

    try:
        result = supabase.table("profiles").update({"avatar_url": data.avatar_url}) \
            .eq("user_id", user_id).execute()

        if hasattr(result, 'error') and result.error:
            raise HTTPException(status_code=400, detail="Ошибка обновления аватара")

        return {"message": "Аватар обновлён"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.patch("/update_email")
def update_email(data: UpdateEmail):
    try:
        response = supabase.auth.update_user(           
            attributes={"email": data.email},
        )
        
        # Проверяем наличие ошибки
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=400,
                detail=response.error.message or "Ошибка обновления почты"
            )
            
        return {"message": "Письмо с подтверждением смены почты выслано"}
        
    except Exception as e:
        print(str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}",
        )

@router.patch("/update_password")
def update_password(data: UpdatePassword):
    try:
        response = supabase.auth.update_user(           
            attributes={"password": data.password},
        )
        
        # Проверяем наличие ошибки
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=400,
                detail=response.error.message or "Ошибка обновления пароля"
            )
            
        return {"message": "Пароль успешно изменен"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )