from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise ValueError("FERNET_KEY is not set in the .env file")
fernet = Fernet(FERNET_KEY)


ALLOWED_EXTENSIONS = {"pptx", "docx", "xlsx"}

def encrypt_token(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_token(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

def allowed_file(filename: str) -> bool:
    return filename.split(".")[-1] in ALLOWED_EXTENSIONS
