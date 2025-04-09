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

router = APIRouter(prefix="/chat")

@router.post("/")
async def del_text_channels(): {
    
}