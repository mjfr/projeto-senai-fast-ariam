from fastapi import APIRouter, Depends, HTTPException, Response, Query
from typing import List, Optional
from app.schemas.tecnico import Tecnico, TecnicoCreate, DadosBancarios, TecnicoUpdate, DadosBancariosUpdate
from app.repositories.in_memory_repository import InMemoryRepository
from app.core.security import hash_password, require_admin_role, get_current_active_user, verify_password
from app.schemas.token import PasswordUpdate

router = APIRouter()


# Função de injeção para o repositório de técnicos
def get_tecnico_repository():
    return InMemoryRepository("tecnicos")


@router.post("/", response_model=Tecnico, status_code=201)
def create_tecnico(
        tecnico_in: TecnicoCreate,
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        admin_user: dict = Depends(require_admin_role)
):
    tecnico_data = tecnico_in.dict()
    plain_password = tecnico_data.pop("password")
    tecnico_data["password_hash"] = hash_password(plain_password)
    tecnico_criado_dict = repo.create(tecnico_data)
    return Tecnico(**tecnico_criado_dict)


@router.get("/", response_model=List[Tecnico])
def get_todos_tecnicos(
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        is_active: Optional[bool] = Query(None, description="Filtra técnicos pelo status de atividade"),
        admin_user: dict = Depends(require_admin_role)
):
    tecnicos_list = repo.get_all(is_active=is_active)
    return [Tecnico(**tecnico) for tecnico in tecnicos_list]


@router.get("/{tecnico_id}", response_model=Tecnico)
def get_tecnico_por_id(
        tecnico_id: int,
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        admin_user: dict = Depends(require_admin_role)
):
    tecnico_encontrado = repo.get_by_id(tecnico_id)
    if not tecnico_encontrado:
        raise HTTPException(status_code=404, detail="Técnico não encontrado")

    return Tecnico(**tecnico_encontrado)


@router.patch("/{tecnico_id}", response_model=Tecnico)
def update_tecnico(
        tecnico_id: int,
        tecnico_in: TecnicoUpdate,
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        admin_user: dict = Depends(require_admin_role)
):
    update_data = tecnico_in.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    updated_tecnico = repo.update(tecnico_id, update_data)
    if updated_tecnico is None:
        raise HTTPException(status_code=404, detail="Técnico não encontrado.")

    return Tecnico(**updated_tecnico)


@router.patch("/me/password", status_code=204)
def update_current_user_password(
        password_data: PasswordUpdate,
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        current_user: dict = Depends(get_current_active_user)
):
    """
    Permite que o usuário logado altere sua própria senha.
    """
    user_id = current_user.get("user_id")

    user_db = repo.get_by_id(user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    current_hash = user_db.get("password_hash")
    if not verify_password(password_data.old_password, current_hash):
        raise HTTPException(status_code=400, detail="Senha antiga incorreta.")

    new_password_hash = hash_password(password_data.new_password)
    repo.update(user_id, {"password_hash": new_password_hash})

    return Response(status_code=204)


@router.delete("/{tecnico_id}", status_code=204)
def delete_tecnico(
        tecnico_id: int,
        repo: InMemoryRepository = Depends(get_tecnico_repository),
        admin_user: dict = Depends(require_admin_role)
):
    success = repo.delete(tecnico_id)
    if not success:
        raise HTTPException(status_code=404, detail="Técnico não encontrado.")
    return Response(status_code=204)


# TODO: Depois ver se vale a pena adicionar um endpoint para o técnico ver suas próprias informações