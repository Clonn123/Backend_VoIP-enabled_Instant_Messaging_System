from pydantic import BaseModel, EmailStr
from datetime import date

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    first_name: str
    birth_date: date

class UserLogin(BaseModel):
    email: EmailStr
    password: str