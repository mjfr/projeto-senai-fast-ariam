from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List
from datetime import date
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate
from app.repositories.in_memory_repository import InMemoryRepository
from app.schemas.visita import Visita, VisitaCreate
from app.schemas.custo import CustoTotalResponse
from app.services.custo_service import CustoService

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


@router.post("/{chamado_id}/visitas", response_model=Visita, status_code=201)
def add_visita_ao_chamado(
    chamado_id: int,
    visita_in: VisitaCreate,
    repo: InMemoryRepository = Depends(get_chamado_repository)
):
   chamado = repo.get_by_id(chamado_id)
   if not chamado:
       raise HTTPException(status_code=404, detail="Chamado não encontrado")

   visita_data = visita_in.dict()

   if not chamado['visitas']:
       visita_id = 1
   else:
       visita_id = max(v['id'] for v in chamado['visitas']) + 1

   visita_data['id'] = visita_id

   chamado['visitas'].append(visita_data)

   repo.update(chamado_id, {'visitas': chamado['visitas']})

   return Visita(**visita_data)


@router.get("/{chamado_id}/custos", response_model=CustoTotalResponse)
def get_custos_do_chamado(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository)
):
    chamado = repo.get_by_id(chamado_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    service = CustoService()

    custos = service.calcular_custo_chamado(chamado)

    return custos