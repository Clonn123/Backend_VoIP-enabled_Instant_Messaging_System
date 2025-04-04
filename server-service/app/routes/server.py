from fastapi import APIRouter, HTTPException, Depends, Request
from ..database import supabase
from ..schemas import ServerCreate, ServerUpdate, ServerMember

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
            .select("*") \
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



# @router.get("/{server_id}")
# async def get_server(server_id: str, user = Depends(get_current_user)):
#     try:
#         # Проверяем доступ к серверу
#         member = supabase.table("server_members") \
#             .select("*") \
#             .eq("user_id", user.user.id) \
#             .eq("server_id", server_id) \
#             .maybe_single() \
#             .execute()
        
#         if not member.data:
#             raise HTTPException(status_code=403, detail="Access denied")
        
#         # Получаем данные сервера
#         server = supabase.table("servers") \
#             .select("*") \
#             .eq("id", server_id) \
#             .single() \
#             .execute()
            
#         return server.data
        
#     except Exception as e:
#         raise HTTPException(status_code=404, detail="Server not found")

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

# @router.post("/{server_id}/members")
# async def add_member(
#     server_id: str,
#     member: ServerMember,
#     user = Depends(get_current_user)
# ):
#     try:
#         # Проверяем права (только owner/admin могут добавлять участников)
#         requester = supabase.table("server_members") \
#             .select("role") \
#             .eq("user_id", user.user.id) \
#             .eq("server_id", server_id) \
#             .in_("role", ["owner", "admin"]) \
#             .maybe_single() \
#             .execute()
            
#         if not requester.data:
#             raise HTTPException(status_code=403, detail="Insufficient permissions")
        
#         # Добавляем участника
#         result = supabase.table("server_members").insert(member.dict()).execute()
#         return result.data[0]
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))