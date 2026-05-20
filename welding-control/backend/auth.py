from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["auth"])

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)

@router.post("/login")
async def login(data: dict, db: Session = Depends(get_db)):
    """
    Проверка логина и пароля
    """
    login = data.get('login')
    password = data.get('password')
    
    if not login or not password:
        raise HTTPException(status_code400, detail="Введите логин и пароль")
    
    user = db.query(User).filter(User.login == login).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "login": user.login
        }
    }