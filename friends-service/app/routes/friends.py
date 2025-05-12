from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import uuid4
from ..database import supabase
from ..schemas import FriendRequest

router = APIRouter(prefix="/friends")

async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        return supabase.auth.get_user(token)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/request")
async def send_friend_request(data: FriendRequest, user=Depends(get_current_user)):
    sender_id = user.user.id
    profile = supabase.table("profiles") \
            .select("*") \
            .eq("user_id", sender_id) \
            .single() \
            .execute()
    sender_username = profile.data.get("username")
    receiver_username = data.receiver_username

    # Получаем профиль по username
    receiver_profile = supabase.table("profiles") \
        .select("user_id") \
        .eq("username", receiver_username) \
        .maybe_single() \
        .execute()
    
    if not receiver_profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    receiver_id = receiver_profile.data["user_id"]
    
    if sender_id == receiver_id:
        raise HTTPException(status_code=400, detail="Нельзя добавить самого себя")

    # Проверка на существующую заявку или дружбу
    sent = supabase.table("friends") \
        .select("id") \
        .eq("sender_id", sender_id) \
        .eq("receiver_id", receiver_id) \
        .maybe_single() \
        .execute()

    received = supabase.table("friends") \
        .select("id") \
        .eq("sender_id", receiver_id) \
        .eq("receiver_id", sender_id) \
        .maybe_single() \
        .execute()

    if (sent and sent.data) or (received and received.data):
        raise HTTPException(status_code=400, detail="Вы уже отправили заявку или уже друзья")

    supabase.table("friends").insert({
        "id": str(uuid4()),
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "status": "pending",
        "sender_name": sender_username,
        "receiver_name": receiver_username,
    }).execute()

    return {"message": "Заявка отправлена"}

@router.patch("/respond")
async def respond_to_request(data: FriendRequest, user=Depends(get_current_user)):
    receiver_id = user.user.id
    sender_username = data.receiver_username  # переворачиваем

    # Получаем профиль по username
    sender_profile = supabase.table("profiles") \
        .select("user_id") \
        .eq("username", sender_username) \
        .maybe_single() \
        .execute()
    
    if not sender_profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    sender_id = sender_profile.data["user_id"]

    if data.status not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Неверный статус")

    # Проверка наличия заявки
    request = supabase.table("friends") \
        .select("*") \
        .eq("sender_id", sender_id) \
        .eq("receiver_id", receiver_id) \
        .eq("status", "pending") \
        .single() \
        .execute()

    if not request.data:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    supabase.table("friends") \
        .update({"status": data.status}) \
        .eq("id", request.data["id"]) \
        .execute()

    return {"message": f"Заявка {data.status}"}

@router.get("/friendsList")
async def get_friends(user=Depends(get_current_user)):
    user_id = user.user.id

    # Друзья = где accepted и user — участник
    friends = supabase.table("friends") \
        .select("*") \
        .or_(
            f"and(sender_id.eq.{user_id},status.eq.accepted),and(receiver_id.eq.{user_id},status.eq.accepted)"
        ) \
        .execute()

    friend_ids = [
        f["receiver_id"] if f["sender_id"] == user_id else f["sender_id"]
        for f in friends.data
    ]

    profiles = supabase.table("profiles") \
        .select("user_id, username, first_name, avatar_url") \
        .in_("user_id", friend_ids) \
        .execute()

    return profiles.data

@router.get("/requests")
async def get_friend_requests(user=Depends(get_current_user)):
    user_id = user.user.id

    incoming = supabase.table("friends") \
        .select("*") \
        .eq("receiver_id", user_id) \
        .eq("status", "pending") \
        .execute()

    outgoing = supabase.table("friends") \
        .select("*") \
        .eq("sender_id", user_id) \
        .or_("status.eq.pending,status.eq.rejected") \
        .execute()

    return {
        "incoming": incoming.data,
        "outgoing": outgoing.data
    }

@router.delete("/cancel-request/{requestId}")
async def cancel_friend_request(requestId: str, user=Depends(get_current_user)):
    supabase.table("friends") \
        .delete() \
        .eq("id", requestId) \
        .execute()

    return {"message": "Заявка отменена"}

@router.get("/{user_id}")
async def get_profile(user_id: str):
    profile = supabase.table("profiles") \
        .select("user_id, username, first_name, avatar_url") \
        .eq("user_id", user_id) \
        .single() \
        .execute()

    if not profile.data:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    return profile.data

@router.delete("/remove/{friend_id}")
async def remove_friend(friend_id: str, user=Depends(get_current_user)):
    user_id = user.user.id

    friendship = supabase.table("friends") \
        .select("*") \
        .or_(
            f"and(sender_id.eq.{user_id},receiver_id.eq.{friend_id},status.eq.accepted)," +
            f"and(sender_id.eq.{friend_id},receiver_id.eq.{user_id},status.eq.accepted)"
        ) \
        .maybe_single() \
        .execute()

    if not friendship or not friendship.data:
        raise HTTPException(status_code=404, detail="Дружба не найдена")

    # Удаляем найденную заявку
    supabase.table("friends") \
        .delete() \
        .eq("id", friendship.data["id"]) \
        .execute()

    return {"message": "Друг удалён"}