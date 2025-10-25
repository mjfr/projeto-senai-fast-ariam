from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from app.repositories.in_memory_repository import InMemoryRepository
from app.core.security import verify_password, create_access_token
from app.schemas.token import Token
from app.api.endpoints.tecnicos import get_tecnico_repository

router = APIRouter()

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    repo: InMemoryRepository = Depends(get_tecnico_repository)
) -> Any:
    """
    Autentica um usuário (técnico) e retorna um token JWT.
    Espera dados de formulário: 'username' (será o email) e 'password'.
    """
    tecnicos = repo.get_all(is_active=None)
    user = None
    for tecnico in tecnicos:
        if tecnico.get('email', '').lower() == form_data.username.lower():
            if not tecnico.get('is_active', False):
                 raise HTTPException(status_code=400, detail="Usuário inativo")
            if verify_password(form_data.password, tecnico.get('password_hash', '')):
                 user = tecnico
                 break
            else:
                 raise HTTPException(
                     status_code=status.HTTP_401_UNAUTHORIZED,
                     detail="Email ou senha incorretos",
                     headers={"WWW-Authenticate": "Bearer"},
                 )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_role = user.get("role", "tecnico") # Fallback para evitar que o role de admin escape por engano

    access_token_data = {
        "sub": user['email'], # Nesse caso (do token), o sub (subject) é o identificador único e não o id.
        "user_id": user['id'],
        "role": user_role,
    }

    access_token = create_access_token(data=access_token_data)

    return {"access_token": access_token, "token_type": "bearer"}