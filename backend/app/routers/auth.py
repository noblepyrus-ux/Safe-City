"""
Router para autenticación y registro de usuarios.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from app.database import get_db
from app.models.user import UserCreate, UserResponse, UserLogin, Token, UserRole
from app.services.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user: UserCreate, db=Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema.
    La contraseña se hashea antes de guardarse.
    """
    # Verificar si el usuario ya existe
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado"
        )
    
    # Verificar si el email ya existe
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Hashear la contraseña
    hashed_password = get_password_hash(user.password)
    
    # Crear el documento del usuario
    user_dict = user.model_dump()
    user_dict["password"] = hashed_password
    user_dict["is_active"] = True
    
    # Insertar en la base de datos
    result = await db.users.insert_one(user_dict)
    
    # Recuperar el usuario creado
    created_user = await db.users.find_one({"_id": result.inserted_id})
    created_user["_id"] = str(created_user["_id"])
    del created_user["password"]  # No devolver la contraseña
    
    return created_user


@router.post("/login", response_model=Token)
async def login(user: UserLogin, db=Depends(get_db)):
    """
    Inicia sesión y devuelve un token JWT.
    """
    # Buscar el usuario
    db_user = await db.users.find_one({"username": user.username})
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    # Verificar la contraseña
    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    # Verificar que el usuario esté activo
    if not db_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
    
    # Crear el token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"], "role": db_user["role"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Obtiene la información del usuario actual autenticado.
    """
    del current_user["password"]  # No devolver la contraseña
    return current_user