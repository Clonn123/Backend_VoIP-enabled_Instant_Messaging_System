from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request
from ..database import supabase
from ..schemas import ServerCreate, InviteResponse, InviteCreate, TextChannel, TextChannelCreate, VoiceChannel, VoiceChannelCreate
from uuid import UUID
from typing import List
import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

@router.post("/{server_id}/invites")
async def create_invite(
    server_id: str,
    invite: InviteCreate,
    user = Depends(get_current_user)
):
    recipient_profile = supabase.table("profiles") \
        .select("user_id, username") \
        .eq("username", invite.recipient_username) \
        .maybe_single() \
        .execute()
    
    if not recipient_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    recipient_id = recipient_profile.data["user_id"]
    # Проверяем, что пользователь не уже участник
    existing_member = supabase.table("server_members") \
        .select("*") \
        .eq("server_id", server_id) \
        .eq("user_id", recipient_id) \
        .maybe_single() \
        .execute()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="The user is already on the server")
    
    existing_invite = supabase.table("server_invites") \
        .select("*") \
        .eq("server_id", server_id) \
        .eq("recipient_username", invite.recipient_username) \
        .eq("status", "pending") \
        .maybe_single() \
        .execute()
    
    if existing_invite:
        raise HTTPException(
            status_code=400, 
            detail="The invitation has already been sent"
        )
    # Создаем приглашение
    new_invite = {
        "server_id": server_id,
        "sender_id": user.user.id,
        "recipient_id": recipient_id,
        "recipient_username": invite.recipient_username,
        "status": "pending",
    }

    result = supabase.table("server_invites").insert(new_invite).execute()
    return result.data[0]

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

@router.delete("/{server_id}/del/textchannels/{channel_id}")
async def del_text_channels(
    server_id: str, 
    channel_id: str, 
    user = Depends(get_current_user)
):
    try:
        # 1. Проверяем права пользователя (только owner/admin могут удалять каналы)
        member = supabase.table("server_members") \
            .select("role") \
            .eq("server_id", server_id) \
            .eq("user_id", user.user.id) \
            .in_("role", ["owner", "admin"]) \
            .maybe_single() \
            .execute()
        
        if not member:
            raise HTTPException(status_code=403, detail="Нет прав")
        
        # 3. Удаляем канал
        supabase.table("text_channels") \
            .delete() \
            .eq("id", channel_id) \
            .execute()
        return {"message": "Канал успешно удален"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении канала: {str(e)}"
        )
    
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
        
        if not member:
            raise HTTPException(status_code=403, detail="Нет прав")
        
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
    
# Голосовые каналы
@router.get("/{server_id}/voicechannels")
async def get_voice_channels(server_id: str, user=Depends(get_current_user)):
    try:
        response = supabase.table("voice_channels") \
            .select("*") \
            .eq("server_id", server_id) \
            .order("position") \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{server_id}/add/voicechannels")
async def create_voice_channel(server_id: str, channel_data: VoiceChannelCreate, user=Depends(get_current_user)):
    try:
        member = supabase.table("server_members") \
            .select("role") \
            .eq("server_id", server_id) \
            .eq("user_id", user.user.id) \
            .in_("role", ["owner", "admin"]) \
            .maybe_single() \
            .execute()
        if not member or not member.data:
            raise HTTPException(status_code=403, detail="Нет прав")

        # Определяем позицию
        last = supabase.table("voice_channels") \
            .select("position") \
            .eq("server_id", server_id) \
            .order("position", desc=True) \
            .limit(1) \
            .execute()
        max_pos = last.data[0]["position"] if last.data else 0

        new_channel = {
            "server_id": server_id,
            "name": channel_data.name,
            "description": channel_data.description,
            "is_private": channel_data.is_private,
            "position": max_pos + 1
        }

        result = supabase.table("voice_channels") \
            .insert(new_channel, returning="representation") \
            .execute()

        return result.data[0]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete("/{server_id}/del/voicechannels/{channel_id}")
async def delete_voice_channel(server_id: str, channel_id: str, user=Depends(get_current_user)):
    try:
        member = supabase.table("server_members") \
            .select("role") \
            .eq("server_id", server_id) \
            .eq("user_id", user.user.id) \
            .in_("role", ["owner", "admin"]) \
            .maybe_single() \
            .execute()
        if not member or not member.data:
            raise HTTPException(status_code=403, detail="Нет прав")

        supabase.table("voice_channels") \
            .delete() \
            .eq("id", channel_id) \
            .execute()

        return {"message": "Голосовой канал удалён"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")

@router.delete("/{server_id}")
async def delete_server(
    server_id: str,
    user = Depends(get_current_user)
):
    """
    Удаляет сервер и все связанные данные (каналы, участники и т.д.)
    Только владелец сервера может удалить сервер
    """
    try:
        member = supabase.table("server_members") \
            .select("role") \
            .eq("server_id", server_id) \
            .eq("user_id", user.user.id) \
            .in_("role", ["owner"]) \
            .maybe_single() \
            .execute()
        
        if not member:
            raise HTTPException(status_code=403, detail="Нет прав")
        
        # Удаляем текстовые каналы
        supabase.table("text_channels") \
            .delete() \
            .eq("server_id", server_id) \
            .execute()
        # Удаляем сам сервер
        supabase.table("servers") \
            .delete() \
            .eq("id", server_id) \
            .execute()

        # 3. Очищаем связанные данные в Cloudinary (если есть аватар)

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении сервера: {str(e)}"
        )

@router.get("/invites/received")
async def get_received_invites(user = Depends(get_current_user)):
    try:
        # Получаем приглашения где текущий пользователь - получатель
        invites = supabase.table("server_invites") \
        .select("*, servers!fk_server(name), sender:profiles!fk_sender(username)") \
        .eq("recipient_id", user.user.id) \
        .eq("status", "pending") \
        .execute()
        
        return invites.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/invites/sent")
async def get_sent_invites(user = Depends(get_current_user)):
    try:
        # Получаем приглашения где текущий пользователь - отправитель
        invites = supabase.table("server_invites") \
            .select("*, servers!fk_server(name), profiles!recipient_id(username)") \
            .eq("sender_id", user.user.id) \
            .execute()
        
        return invites.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/invites/{invite_id}/respond")
async def respond_to_invite(invite_id: UUID, response: InviteResponse, user=Depends(get_current_user)):
    try:
        if response.status not in ("accepted", "rejected"):
            raise HTTPException(status_code=400, detail="Недопустимый статус")
        invite_response = supabase.table("server_invites") \
            .select("*") \
            .eq("id", str(invite_id)) \
            .eq("recipient_id", user.user.id) \
            .single() \
            .execute()

        invite = invite_response.data
        if not invite:
            raise HTTPException(status_code=404, detail="Приглашение не найдено")

        # Обновляем статус
        supabase.table("server_invites") \
            .update({"status": response.status}) \
            .eq("id", str(invite_id)) \
            .execute()
            
        if response.status == "accepted":
            supabase.table("server_members") \
                .insert({
                    "server_id": invite["server_id"],
                    "user_id": user.user.id
                }) \
                .execute()

        return {"message": f"Приглашение {response.status}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке приглашения: {e}")
@router.delete("/invites/{invite_id}")
async def cancel_invite(invite_id: UUID, user=Depends(get_current_user)):
    try:
        # Удаляем приглашение
        supabase.table("server_invites") \
            .delete() \
            .eq("id", str(invite_id)) \
            .execute()

        return {"message": "Приглашение отменено"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении приглашения: {e}")
@router.get("/invites/requests")
async def check_incoming_requests(user=Depends(get_current_user)):
    try:
        response = supabase.table("server_invites") \
            .select("id") \
            .eq("recipient_id", user.user.id) \
            .eq("status", "pending") \
            .execute()

        invites = response.data or []

        return {"incoming": invites}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке входящих заявок: {e}")
    
#Сессии голосовых каналов (пока БД, потом Redis или иное)
@router.post("/{server_id}/voicechannels/{channel_id}/join")
async def join_voice_channel(channel_id: str, user=Depends(get_current_user)):
    try:
        supabase.table("voice_sessions").insert({
            "channel_id": channel_id,
            "user_id": user.user.id
        }).execute()
        return {"message": "User joined voice channel"}
    except Exception as e:
        if "duplicate key" in str(e):
            return {"message": "Already in voice channel"}
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{server_id}/voicechannels/{channel_id}/leave")
async def leave_voice_channel(channel_id: str, user=Depends(get_current_user)):
    try:
        supabase.table("voice_sessions") \
            .delete() \
            .eq("channel_id", channel_id) \
            .eq("user_id", user.user.id) \
            .execute()
        return {"message": "Left voice channel"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{server_id}/voicechannels/{channel_id}/members")
async def get_voice_members(channel_id: str):
    try:
        threshold = (datetime.utcnow() - timedelta(seconds=6)).isoformat()

        # Удаляем "мертвые" сессии
        supabase.table("voice_sessions") \
            .delete() \
            .lt("last_seen", threshold) \
            .eq("channel_id", channel_id) \
            .execute()
        
        # Получаем всех user_id из voice_sessions
        response = supabase.table("voice_sessions") \
            .select("user_id") \
            .eq("channel_id", channel_id) \
            .execute()

        user_ids = [entry["user_id"] for entry in response.data]

        # Получаем профили по этим user_id
        profiles = supabase.table("profiles") \
            .select("user_id, username, avatar_url") \
            .in_("user_id", user_ids) \
            .execute()

        return profiles.data

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{server_id}/voicechannels/{channel_id}/heartbeat")
async def heartbeat(channel_id: str, user=Depends(get_current_user)):
    try:
        supabase.table("voice_sessions") \
            .update({"last_seen": "now()"}) \
            .eq("channel_id", channel_id) \
            .eq("user_id", user.user.id) \
            .execute()
        return {"status": "updated"}
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
