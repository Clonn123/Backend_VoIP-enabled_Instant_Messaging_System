from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: str
    birth_date: date

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UpdateUsername(BaseModel):
    username: str

class UpdateFirstName(BaseModel):
    first_name: str

class UpdateAvatar(BaseModel):
    avatar_url: str

class UpdateEmail(BaseModel):
    email: EmailStr

class UpdatePassword(BaseModel):
    password: str