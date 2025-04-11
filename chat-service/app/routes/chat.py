from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request
from ..database import supabase
from ..schemas import Server, ServerUpdate, ServerMember, TextChannel, TextChannelCreate
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

router = APIRouter(prefix="/chat")

@router.post("/{chat_id}")
async def get_chat(
    server_id: Server,
    chat_id: str, 
    user = Depends(get_current_user)
):
    try:
        chat = supabase.table("text_channels") \
            .select("*") \
            .eq("id", chat_id) \
            .eq("server_id", server_id.server_id) \
            .maybe_single() \
            .execute()

        if not chat.data:
            raise HTTPException(
                status_code=404,
                detail="Chat not found"
            )
        
        return chat.data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))