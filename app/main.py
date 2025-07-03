
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.responses import FileResponse
import shutil, os, uuid
from app.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.database import SessionLocal, engine, Base
from app.models import User, FileRecord, UserRole
from app.schemas import UserCreate, UserOut, FileOut
from app.utils import encrypt_token, decrypt_token, allowed_file


Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/client/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, hashed_password=get_password_hash(user.password), role=UserRole.CLIENT)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    encrypted = encrypt_token(str(new_user.id))
    return {"email": new_user.email, "encrypted_url": f"/client/verify-email/{encrypted}"}

@app.get("/client/verify-email/{token}")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        user_id = decrypt_token(token)
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_verified = True
        db.commit()
        return {"message": "Email verified successfully"}
    except:
        raise HTTPException(status_code=400, detail="Invalid token")

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token(data={"sub": str(user.id)}), "token_type": "bearer"}

@app.post("/ops/upload")
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.OPS:
        raise HTTPException(status_code=403, detail="Only ops can upload")
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    fid = str(uuid.uuid4()) + "_" + file.filename
    path = os.path.join(UPLOAD_DIR, fid)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    db_file = FileRecord(filename=fid, uploader_id=user.id)
    db.add(db_file)
    db.commit()
    return {"message": "File uploaded"}

@app.get("/client/files", response_model=list[FileOut])
def list_files(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Only client can list files")
    return db.query(FileRecord).all()

@app.get("/client/download/{file_id}")
def get_download_url(file_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Only client can download")
    file = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    token = encrypt_token(f"{file_id}:{user.id}")
    return {"download_link": f"/download/{token}"}

@app.get("/download/{token}")
def download_file(token: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        file_id, requester_id = decrypt_token(token).split(":")
        if str(user.id) != requester_id or user.role != UserRole.CLIENT:
            raise HTTPException(status_code=403, detail="Access denied")
        file = db.query(FileRecord).filter(FileRecord.id == int(file_id)).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(path=os.path.join(UPLOAD_DIR, file.filename), filename=file.filename)
    except:
        raise HTTPException(status_code=400, detail="Invalid download token")
