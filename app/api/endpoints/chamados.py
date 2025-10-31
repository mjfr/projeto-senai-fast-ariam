from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional
from datetime import date

from app.api.endpoints.tecnicos import get_tecnico_repository
from app.core.security import get_current_active_user, require_admin_role, require_technician_role
from app.repositories.in_memory_repository import InMemoryRepository
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate
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
        repo: InMemoryRepository = Depends(get_chamado_repository),
        admin_user: dict = Depends(require_admin_role)
):
    chamado_data = chamado_in.dict()
    chamado_data['data_abertura'] = date.today()
    chamado_data['visitas'] = []
    chamado_data['is_cancelled'] = False

    chamado_criado_dict = repo.create(chamado_data)
    return Chamado(**chamado_criado_dict)


@router.get("/", response_model=List[Chamado])
def get_todos_chamados(
        repo: InMemoryRepository = Depends(get_chamado_repository),
        is_cancelled: Optional[bool] = Query(None, description="Filtra chamados pelo status de cancelamento"),
        current_user: dict = Depends(get_current_active_user)
):
    chamados_list = repo.get_all()
    response_list = []
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    for chamado_db in chamados_list:
        is_chamado_cancelado = chamado_db.get("is_cancelled", False)
        id_tecnico_atribuido = chamado_db.get("id_tecnico_atribuido")

        if is_cancelled is not None and is_chamado_cancelado != is_cancelled:
            continue

        if user_role == "tecnico":
            if id_tecnico_atribuido != user_id:
                continue

        response_list.append(Chamado(**chamado_db))

    return response_list


@router.get("/{chamado_id}", response_model=Chamado)
def get_chamado_por_id(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    chamado_encontrado = repo.get_by_id(chamado_id)
    if not chamado_encontrado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    id_tecnico_atribuido = chamado_encontrado.get("id_tecnico_atribuido")

    if user_role == "tecnico" and id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este chamado.")

    return Chamado(**chamado_encontrado)


@router.patch("/{chamado_id}", response_model=Chamado)
def update_chamado(
        chamado_id: int,
        chamado_in: ChamadoUpdate,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        tecnico_repo: InMemoryRepository = Depends(get_tecnico_repository),
        admin_user: dict = Depends(require_admin_role)
):
    update_data = chamado_in.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    if 'id_tecnico_atribuido' in update_data:
        novo_tecnico_id = update_data['id_tecnico_atribuido']
        if novo_tecnico_id is not None:
            tecnico_db = tecnico_repo.get_by_id(novo_tecnico_id)
            if not tecnico_db or not tecnico_db.get('is_active', True):
                raise HTTPException(status_code=404, detail=f"Técnico com id {novo_tecnico_id} não encontrado ou inativo.")
            if 'status' not in update_data:
                update_data['status'] = 'Agendado'

    novo_status = update_data.get("status")
    if novo_status == "Finalizado":
        update_data['data_conclusao'] = date.today()
    elif novo_status != "Finalizado":
        update_data['data_conclusao'] = None

    updated_chamado = repo.update(chamado_id, update_data)
    if updated_chamado is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    cliente_final_id = updated_chamado.get('cliente_id')

    resposta_completa = updated_chamado.copy()
    return Chamado(**resposta_completa)


@router.delete("/{chamado_id}", status_code=204)
def delete_chamado(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        admin_user: dict = Depends(require_admin_role)
):
    success = repo.delete(chamado_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    return Response(status_code=204)


@router.post("/{chamado_id}/visitas", response_model=Visita, status_code=201)
def add_visita_ao_chamado(
        chamado_id: int,
        visita_in: VisitaCreate,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user),
):
    """
    Adiciona uma nova visita ao chamado.
    Requer que o usuário esteja autenticado com um token JWT válido
    """
    logged_user_id = current_user["user_id"]

    chamado = repo.get_by_id(chamado_id)
    if not chamado or chamado.get('is_cancelled', False):
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.get('id_tecnico_atribuido') != logged_user_id:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Você não tem permissão para adicionar uma visita neste chamado.")

    visita_data = visita_in.dict()

    if not chamado.get('visitas'):
        chamado['visitas'] = []
        visita_id = 1
    else:
        visita_id = max(v.get('id', 0) for v in chamado['visitas']) + 1

    visita_data['id'] = visita_id
    chamado['visitas'].append(visita_data)

    dados_update_chamado = {"visitas": chamado['visitas']}
    if not visita_in.servico_finalizado and visita_in.pendencia:
        dados_update_chamado['status'] = "Pendente"
    elif visita_in.servico_finalizado:
        dados_update_chamado['status'] = "Em Atendimento"

    repo.update(chamado_id, dados_update_chamado)

    return Visita(**visita_data)


@router.get("/{chamado_id}/custos", response_model=CustoTotalResponse)
def get_custos_do_chamado(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    chamado = repo.get_by_id(chamado_id)
    if not chamado or chamado.get('is_cancelled', False):
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    id_tecnico_atribuido = chamado.get('id_tecnico_atribuido')

    if user_role == "tecnico" and id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado aos custos deste chamado.")

    service = CustoService()
    custos = service.calcular_custo_chamado(chamado)
    return custos
