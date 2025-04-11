from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class FriendRequest(BaseModel):
    receiver_username: str
    status: str = "pending"