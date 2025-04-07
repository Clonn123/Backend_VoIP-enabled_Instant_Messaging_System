from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request
from ..database import supabase
from ..schemas import ServerCreate, ServerUpdate, ServerMember, TextChannel, TextChannelCreate
from uuid import UUID
from typing import List
import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv

load_dotenv()
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

router = APIRouter(prefix="/servers")

@router.post("/")
async def create_server(
    server: ServerCreate,
    user = Depends(get_current_user)
):
    try:
        # Создаем сервер
        server_data = {
            "name": server.name,
            "image_url": server.image_url,
            "owner_id": user.user.id
        }
        
        result = supabase.table("servers").insert(server_data).execute()
        new_server = result.data[0]
        
        # Добавляем владельца как участника
        member_data = {
            "user_id": user.user.id,
            "server_id": new_server["id"],
            "role": "owner"
        }
        supabase.table("server_members").insert(member_data).execute()
        
        return new_server
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/my-servers")
async def get_user_servers(user = Depends(get_current_user)):
    try:
        # 1. Получаем все серверы, где пользователь является участником
        memberships = supabase.table("server_members") \
            .select("server_id, role") \
            .eq("user_id", user.user.id) \
            .execute()
        
        if not memberships.data:
            return []
        
        # 2. Получаем полные данные этих серверов
        server_ids = [m["server_id"] for m in memberships.data]
        servers = supabase.table("servers") \
            .select("id, name, image_url, owner_id") \
            .in_("id", server_ids) \
            .execute()
        
        # 3. Добавляем роль пользователя в каждом сервере
        servers_with_role = []
        for server in servers.data:
            membership = next(m for m in memberships.data if m["server_id"] == server["id"])
            servers_with_role.append({
                **server,
                "user_role": membership["role"]
            })
        
        return servers_with_role
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
async def upload_to_cloudinary(file: UploadFile):
    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder="avatar_servers",
            resource_type="auto",
        )
        return result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload error: {str(e)}")

@router.post("/upload-image")
async def upload_image(file: UploadFile):
    try:
        image_url = await upload_to_cloudinary(file)
        return {"url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_id}")
async def get_server(server_id: str, user = Depends(get_current_user)):
    # 1. Проверяем существование сервера
    try:
        server_exists = supabase.table("servers") \
            .select("id", count="exact") \
            .eq("id", server_id) \
            .execute()
        
        if server_exists.count == 0:
            raise HTTPException(status_code=404, detail="Server not found")
    except Exception:
        raise HTTPException(status_code=404, detail="Server not found")

    # 2. Проверяем права доступа
    try:
        member = supabase.table("server_members") \
            .select("role") \
            .eq("user_id", user.user.id) \
            .eq("server_id", server_id) \
            .maybe_single() \
            .execute()

        if not member.data:
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Access denied")

    # 3. Если все проверки пройдены - получаем данные
    try:
        server = supabase.table("servers") \
            .select("*") \
            .eq("id", server_id) \
            .single() \
            .execute()

        return {
            **server.data,
            "user_role": member.data["role"]
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Нужны друзья
@router.post("/{server_id}/members")
async def add_member(
    server_id: str,
    member: ServerMember,
    user = Depends(get_current_user)
):
    try:
        # Проверяем права (только owner/admin могут добавлять участников)
        requester = supabase.table("server_members") \
            .select("role") \
            .eq("user_id", user.user.id) \
            .eq("server_id", server_id) \
            .in_("role", ["owner", "admin"]) \
            .maybe_single() \
            .execute()
            
        if not requester.data:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Добавляем участника
        result = supabase.table("server_members").insert(member.dict()).execute()
        return result.data[0]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{server_id}/textchannels")
async def get_text_channels(
    server_id: str, 
    user = Depends(get_current_user)
):
    try:
        response = supabase.table("text_channels") \
            .select("*") \
            .eq("server_id", server_id) \
            .order("position") \
            .execute()
        
        return response.data 
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/{server_id}/add/textchannels")
async def create_text_channel(
    server_id: str,
    channel_data: TextChannelCreate,
    user = Depends(get_current_user)
):
    try:
        # Проверяем права пользователя (только owner/admin могут создавать каналы)
        member = supabase.table("server_members") \
            .select("role") \
            .eq("server_id", server_id) \
            .eq("user_id", user.user.id) \
            .in_("role", ["owner", "admin"]) \
            .maybe_single() \
            .execute()
        
        if not member.data:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        position_res = supabase.from_("text_channels") \
            .select("position") \
            .eq("server_id", server_id) \
            .order("position", desc=True) \
            .limit(1) \
            .execute()
        
        max_position = position_res.data[0].get("position", 0) if position_res.data else 0
        
        # Создаем канал
        new_channel = {
            "server_id": server_id,
            "name": channel_data.name,
            "description": channel_data.description,
            "position": max_position + 1,
            "is_private": channel_data.is_private or False,
        }
    
        response = supabase.from_("text_channels") \
            .insert(new_channel, returning="representation") \
            .execute()

        return response.data[0]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# @router.put("/{server_id}")
# async def update_server(
#     server_id: str,
#     server: ServerUpdate,
#     user = Depends(get_current_user)
# ):
#     try:
#         # Проверяем права (только owner/admin могут редактировать)
#         member = supabase.table("server_members") \
#             .select("role") \
#             .eq("user_id", user.user.id) \
#             .eq("server_id", server_id) \
#             .in_("role", ["owner", "admin"]) \
#             .maybe_single() \
#             .execute()
            
#         if not member.data:
#             raise HTTPException(status_code=403, detail="Insufficient permissions")
        
#         # Обновляем сервер
#         update_data = {k: v for k, v in server.dict().items() if v is not None}
#         result = supabase.table("servers") \
#             .update(update_data) \
#             .eq("id", server_id) \
#             .execute()
            
#         return result.data[0]
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
