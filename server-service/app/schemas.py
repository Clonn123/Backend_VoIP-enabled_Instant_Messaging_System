from pydantic import BaseModel
from datetime import date
from typing import Optional

# Новые схемы для серверов
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