from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional
from app.schemas.cliente import Cliente, ClienteCreate, ClienteUpdate
from app.repositories.in_memory_repository import InMemoryRepository
from app.core.security import require_admin_role

router = APIRouter()


def get_cliente_repository():
    return InMemoryRepository("clientes")


@router.post("/", response_model=Cliente, status_code=201)
def create_cliente(
        cliente_in: ClienteCreate,
        repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    cliente_data = cliente_in.dict()
    cliente_data['is_active'] = True

    cliente_criado_dict = repo.create(cliente_data)
    return Cliente(**cliente_criado_dict)


@router.get("/", response_model=List[Cliente])
def get_todos_clientes(
        repo: InMemoryRepository = Depends(get_cliente_repository),
        is_active: Optional[bool] = Query(None, description="Filtra clientes pelo status de atividade"),
        admin_user: dict = Depends(require_admin_role)
):
    clientes_list = repo.get_all(is_active=is_active)
    return [Cliente(**cliente) for cliente in clientes_list]


@router.get("/{cliente_id}", response_model=Cliente)
def get_cliente_por_id(
        cliente_id: int,
        repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    cliente_encontrado = repo.get_by_id(cliente_id)
    if not cliente_encontrado:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return Cliente(**cliente_encontrado)


@router.patch("/{cliente_id}", response_model=Cliente)
def update_cliente(
        cliente_id: int,
        cliente_in: ClienteUpdate,
        repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    update_data = cliente_in.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    updated_cliente = repo.update(cliente_id, update_data)
    if updated_cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return Cliente(**updated_cliente)


@router.delete("/{cliente_id}", status_code=204)
def delete_cliente(
        cliente_id: int,
        repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    success = repo.delete(cliente_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return Response(status_code=204)

# TODO: Depois pensar em liberar o acesso do cliente para o técnico de acordo com o chamado que ele está atendendo