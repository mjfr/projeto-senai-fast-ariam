from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List
from datetime import date
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate
from app.repositories.in_memory_repository import InMemoryRepository

router = APIRouter()


# Injetando o repositório que vai ser utilizado
def get_chamado_repository():
    return InMemoryRepository("chamados")


@router.post("/", response_model=Chamado, status_code=201)
def create_chamado(
        chamado_in: ChamadoCreate,
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    chamado_data = chamado_in.dict()

    chamado_data['data_abertura'] = date.today()
    chamado_data['status'] = "Aberto"
    chamado_data['visitas'] = []
    chamado_data['is_cancelled'] = False

    chamado_criado_dict = repo.create(chamado_data)
    return Chamado(**chamado_criado_dict)


@router.get("/", response_model=List[Chamado])
def get_todos_chamados(
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    chamados_list = repo.get_all()
    return [Chamado(**chamado) for chamado in chamados_list]


@router.get("/{chamado_id}", response_model=Chamado)
def get_chamado_por_id(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    chamado_encontrado = repo.get_by_id(chamado_id)
    if not chamado_encontrado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    return Chamado(**chamado_encontrado)


@router.patch("/{chamado_id}", response_model=Chamado)
def update_chamado(
        chamado_id: int,
        chamado_in: ChamadoUpdate,
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    update_data = chamado_in.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    updated_chamado = repo.update(chamado_id, update_data)
    if updated_chamado is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    return Chamado(**updated_chamado)


@router.delete("/{chamado_id}", status_code=204)
def delete_chamado(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    success = repo.delete(chamado_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    return Response(status_code=204)
