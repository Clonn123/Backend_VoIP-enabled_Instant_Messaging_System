from pydantic import BaseModel
from datetime import date
from typing import Optional

class ServerCreate(BaseModel):
    name: str
    is_public: bool = True
    image_url: str

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class ServerMember(BaseModel):
    user_id: str
    server_id: str
    role: str  # "owner", "admin", "member"
class TextChannel(BaseModel):
    id: str
    server_id: str
    name: str
    description: str | None
    position: str
    is_private: bool
    created_at: str
    updated_at: str
class TextChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False