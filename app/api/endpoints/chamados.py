from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional
from datetime import date
# from app.api.endpoints.clientes import get_cliente_repository
from app.core.security import get_current_active_user, require_admin_role, require_technician_role
from app.repositories.in_memory_repository import InMemoryRepository
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate
from app.schemas.visita import Visita, VisitaCreate
from app.schemas.custo import CustoTotalResponse
# from app.schemas.cliente import Cliente
from app.services.custo_service import CustoService

router = APIRouter()


# Injetando o repositório que vai ser utilizado
def get_chamado_repository():
    return InMemoryRepository("chamados")


@router.post("/", response_model=Chamado, status_code=201)
def create_chamado(
        chamado_in: ChamadoCreate,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        # cliente_repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    # cliente_db = cliente_repo.get_by_id(chamado_in.cliente_id)
    # if not cliente_db or not cliente_db.get("is_active", True):
    #     raise HTTPException(status_code=404,
    #                         detail=f"Cliente com id {chamado_in.cliente_id} não encontrado ou inativo.")

    chamado_data = chamado_in.dict()
    chamado_data['data_abertura'] = date.today()
    chamado_data['status'] = "Aberto"
    chamado_data['visitas'] = []
    chamado_data['is_cancelled'] = False

    chamado_criado_dict = repo.create(chamado_data)
    # chamado_criado_dict['cliente'] = Cliente(**cliente_db)
    return Chamado(**chamado_criado_dict)


@router.get("/", response_model=List[Chamado])
def get_todos_chamados(
        repo: InMemoryRepository = Depends(get_chamado_repository),
        # cliente_repo: InMemoryRepository = Depends(get_cliente_repository),
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

        # cliente_db = cliente_repo.get_by_id(chamado_db.get('cliente_id'))
        # if cliente_db:
        #     chamado_completo = chamado_db.copy()
            # chamado_completo['cliente'] = Cliente(**cliente_db)
            # response_list.append(Chamado(**chamado_completo))
        response_list.append(Chamado(**chamado_db))

    return response_list


@router.get("/{chamado_id}", response_model=Chamado)
def get_chamado_por_id(
        chamado_id: int,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        # cliente_repo: InMemoryRepository = Depends(get_cliente_repository),
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

    # cliente_id_chamado = chamado_encontrado.get('cliente_id')
    # if cliente_id_chamado is None:
    #     raise HTTPException(status_code=500, detail="Erro interno: chamado sem cliente_id associado.")

    # cliente_db = cliente_repo.get_by_id(cliente_id_chamado)
    # if not cliente_db:  # TODO: Verificar inconsistência. Se não houver cliente, talvez colocar um None ou um placeholder
    #     raise HTTPException(status_code=500,
    #                         detail=f"Inconsistência de dados: Cliente com ID {cliente_id_chamado} associado ao chamado não foi encontrado.")

    # chamado_completo = chamado_encontrado.copy()
    # chamado_completo['cliente'] = Cliente(**cliente_db)
    return Chamado(**chamado_encontrado)


@router.patch("/{chamado_id}", response_model=Chamado)
def update_chamado(
        chamado_id: int,
        chamado_in: ChamadoUpdate,
        repo: InMemoryRepository = Depends(get_chamado_repository),
        # cliente_repo: InMemoryRepository = Depends(get_cliente_repository),
        admin_user: dict = Depends(require_admin_role)
):
    update_data = chamado_in.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    # if 'cliente_id' in update_data:
    #     novo_cliente_db = cliente_repo.get_by_id(update_data['cliente_id'])
    #     if not novo_cliente_db or not novo_cliente_db.get("is_active", True):
    #         raise HTTPException(status_code=404,
    #                             detail=f"Novo cliente com id {update_data['cliente_id']} não encontrado ou inativo.")

    updated_chamado = repo.update(chamado_id, update_data)
    if updated_chamado is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    cliente_final_id = updated_chamado.get('cliente_id')
    # cliente_final_db = cliente_repo.get_by_id(cliente_final_id)

    resposta_completa = updated_chamado.copy()
    # if cliente_final_db:
    #     resposta_completa['cliente'] = Cliente(
    #         **cliente_final_db)  # TODO: Por enquanto, fica sem cliente se não for encontrado
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
    repo.update(chamado_id, {'visitas': chamado['visitas']})

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
