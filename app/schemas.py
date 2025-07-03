from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    email: EmailStr
    encrypted_url: str

class FileOut(BaseModel):
    id: int
    filename: str

    class Config:
        from_attributes = True
