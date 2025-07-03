from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import User, FileRecord, UserRole
from app.auth import get_password_hash
import os, shutil

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def seed():
    db: Session = SessionLocal()

    db.query(FileRecord).delete()
    db.query(User).delete()
    db.commit()

    ops_user = User(
        email="ops@example.com",
        hashed_password=get_password_hash("adminpass"),
        role=UserRole.OPS,
        is_verified=True
    )

    client_user = User(
        email="client@example.com",
        hashed_password=get_password_hash("clientpass"),
        role=UserRole.CLIENT,
        is_verified=True
    )

    db.add_all([ops_user, client_user])
    db.commit()
    db.refresh(ops_user)

    
    dummy_filename = "test_doc.docx"
    test_file_path = os.path.join(UPLOAD_DIR, dummy_filename)
    with open(test_file_path, "wb") as f:
        f.write(b"Test content")

    db_file = FileRecord(filename=dummy_filename, uploader_id=ops_user.id)
    db.add(db_file)
    db.commit()

    print("Seeded users and one test file")

if __name__ == "__main__":
    seed()