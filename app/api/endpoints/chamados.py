from fastapi import APIRouter, Depends, HTTPException, Query, Response, File, UploadFile, Form
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, require_admin_role, require_technician_role
from app.db.database import get_db
from app.repositories.mysql_repository import SQLRepository
# from app.repositories.in_memory_repository import InMemoryRepository, deep_update
from app.repositories.in_memory_repository import deep_update
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate, StatusChamado
from app.schemas.visita import Visita, VisitaCreate, VisitaUpdate
from app.schemas.custo import CustoTotalResponse
from app.services.custo_service import CustoService
from app.services.file_service import save_upload_file

router = APIRouter()
MULTI_FILE_FIELDS = ["comprovante_pedagio_urls", "comprovante_frete_urls"]
SINGLE_FILE_FIELDS = ["odometro_inicio_url", "odometro_fim_url", "assinatura_cliente_url"]


# Injetando o repositório que vai ser utilizado
# def get_chamado_repository():
#     return InMemoryRepository("chamados")

def get_chamado_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


def get_cliente_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


def get_tecnico_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


@router.post("/", response_model=Chamado, status_code=201)
def create_chamado(
        chamado_in: ChamadoCreate,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        cliente_repo: SQLRepository = Depends(get_cliente_repository),
        _admin_user: dict = Depends(require_admin_role)
):
    cliente_db = cliente_repo.get_cliente_by_id(chamado_in.id_cliente)
    if not cliente_db or not cliente_db.is_active:
        raise HTTPException(status_code=404,
                            detail=f"Cliente com id {chamado_in.id_cliente} não encontrado ou inativo.")

    chamado_data = chamado_in.model_dump()
    chamado_data['data_abertura'] = date.today()
    # chamado_data['visitas'] = []
    chamado_data['is_cancelled'] = False

    # if chamado_data['id_tecnico_atribuido'] is not None:
    #     chamado_data['status'] = "Agendado"

    if chamado_data.get('id_tecnico_atribuido') is not None:
        chamado_data['status'] = StatusChamado.AGENDADO
    else:
        chamado_data['status'] = StatusChamado.ABERTO

    # chamado_criado_dict = repo.create(chamado_data)
    chamado_criado_db = repo.create_chamado(chamado_data)
    # return Chamado(**chamado_criado_dict)
    return chamado_criado_db


@router.get("/", response_model=List[Chamado])
def get_todos_chamados(
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        is_cancelled: Optional[bool] = Query(None, description="Filtra chamados pelo status de cancelamento"),
        current_user: dict = Depends(get_current_active_user)
):
    # chamados_list = repo.get_all()
    chamados_list_db = repo.get_chamados()
    response_list = []
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    # for chamado_db in chamados_list:
    for chamado_db in chamados_list_db:
        # is_chamado_cancelado = chamado_db.get("is_cancelled", False)
        is_chamado_cancelado = chamado_db.is_cancelled
        # id_tecnico_atribuido = chamado_db.get("id_tecnico_atribuido")
        id_tecnico_atribuido = chamado_db.id_tecnico_atribuido

        if is_cancelled is not None and is_chamado_cancelado != is_cancelled:
            continue

        if user_role == "tecnico":
            if id_tecnico_atribuido != user_id:
                continue

        # response_list.append(Chamado(**chamado_db))
        response_list.append(chamado_db)

    return response_list


@router.get("/{chamado_id}", response_model=Chamado)
def get_chamado_por_id(
        chamado_id: int,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    # chamado_encontrado = repo.get_by_id(chamado_id)
    chamado_encontrado = repo.get_chamado_by_id(chamado_id)
    if not chamado_encontrado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    # id_tecnico_atribuido = chamado_encontrado.get("id_tecnico_atribuido")

    # if user_role == "tecnico" and id_tecnico_atribuido != user_id:
    if user_role == "tecnico" and chamado_encontrado.id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este chamado.")

    # return Chamado(**chamado_encontrado)
    return chamado_encontrado


@router.patch("/{chamado_id}", response_model=Chamado)
def update_chamado(
        chamado_id: int,
        chamado_in: ChamadoUpdate,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        # tecnico_repo: InMemoryRepository = Depends(get_tecnico_repository),
        tecnico_repo: SQLRepository = Depends(get_tecnico_repository),
        current_user: dict = Depends(get_current_active_user),
        # _admin_user: dict = Depends(require_admin_role)
):
    """
    O administrador atualiza qualquer dado de um chamado.
    Esse endpoint é utilizado também para atribuir um técnico e uma data de agendamento caso não tenham sido atribuídos na criação do chamado.
    Também permite o administrador reabrir o chamado se necessário.
    """
    update_data = chamado_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    if user_role == "tecnico":
        chamado_db = repo.get_chamado_by_id(chamado_id)
        if not chamado_db or chamado_db.id_tecnico_atribuido != user_id:
            raise HTTPException(status_code=403, detail="Acesso negado a este chamado.")

        allowed_fields = {"status"}
        for field in update_data.keys():
            if field not in allowed_fields:
                raise HTTPException(status_code=403, detail=f"Técnicos não podem atualizar o campo '{field}'.")

    if user_role == "admin":
        if 'id_tecnico_atribuido' in update_data:
            novo_tecnico_id = update_data['id_tecnico_atribuido']
            if novo_tecnico_id is not None:
                tecnico_db = tecnico_repo.get_tecnico_by_id(novo_tecnico_id)
                if not tecnico_db or not tecnico_db.is_active:
                    raise HTTPException(status_code=404,
                                        detail=f"Técnico com id {novo_tecnico_id} não encontrado ou inativo.")
                if 'status' not in update_data:
                    update_data['status'] = StatusChamado.AGENDADO

    novo_status = update_data.get("status")
    if novo_status:
        if novo_status == StatusChamado.FINALIZADO:
            if user_role != "admin":
                raise HTTPException(status_code=403,
                                    detail="Técnicos devem finalizar o chamado através da atualização da visita.")
            update_data['data_conclusao'] = date.today()
        elif novo_status != StatusChamado.FINALIZADO:
            update_data['data_conclusao'] = None

    novo_status = update_data.get("status")
    if novo_status == "Finalizado":
        update_data['data_conclusao'] = date.today()
    elif novo_status != "Finalizado":
        update_data['data_conclusao'] = None

    # if 'id_tecnico_atribuido' in update_data:
    #     novo_tecnico_id = update_data['id_tecnico_atribuido']
    #     if novo_tecnico_id is not None:
    #         tecnico_db = tecnico_repo.get_by_id(novo_tecnico_id)
    #         if not tecnico_db or not tecnico_db.get('is_active', True):
    #             raise HTTPException(status_code=404,
    #                                 detail=f"Técnico com id {novo_tecnico_id} não encontrado ou inativo.")
    #         if 'status' not in update_data:
    #             update_data['status'] = 'Agendado'

    # updated_chamado = repo.update(chamado_id, update_data)
    updated_chamado = repo.update_chamado(chamado_id, update_data)
    if updated_chamado is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    # return Chamado(**updated_chamado)
    return updated_chamado


@router.delete("/{chamado_id}", status_code=204)
def delete_chamado(
        chamado_id: int,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        _admin_user: dict = Depends(require_admin_role)
):
    # success = repo.delete(chamado_id)
    success = repo.delete_chamado(chamado_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    return Response(status_code=204)


@router.post("/{chamado_id}/visitas", response_model=Visita, status_code=201)
def add_visita_ao_chamado(
        chamado_id: int,
        visita_in: VisitaCreate,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user),
):
    """
    Adiciona uma nova visita ao chamado.
    Requer que o usuário esteja autenticado com um token JWT válido
    """
    logged_user_id = current_user["user_id"]

    # chamado = repo.get_by_id(chamado_id)
    chamado = repo.get_chamado_by_id(chamado_id)
    # if not chamado or chamado.get('is_cancelled', False):
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    # if chamado.get('id_tecnico_atribuido') != logged_user_id:
    if chamado.id_tecnico_atribuido != logged_user_id:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Você não tem permissão para adicionar uma visita neste chamado.")

    if visita_in.servico_finalizado:
        raise HTTPException(status_code=400,
                            detail="Não é possível criar uma visita já finalizada. Crie a visita, faça os uploads e depois finalize-a.")

    visita_data = visita_in.model_dump()

    visita_db = repo.create_visita(chamado_id, visita_data)

    # if not chamado.visitas:
    #     chamado['visitas'] = []
    #     visita_id = 1
    # else:
    #     visitas_existentes = chamado.get('visitas', [])
    #     if not visitas_existentes:
    #         visita_id = 1
    #     else:
    #         visita_id = max(v.get('id', 0) for v in visitas_existentes) + 1
    #
    # visita_data['id'] = visita_id
    # chamado['visitas'].append(visita_data)
    #
    # dados_update_chamado = {"visitas": chamado['visitas']}
    # if visita_in.pendencia:
    #     dados_update_chamado['status'] = "Pendente"
    # else:
    #     dados_update_chamado['status'] = "Em Atendimento"
    dados_update_chamado = {}
    if visita_in.pendencia:
        dados_update_chamado['status'] = StatusChamado.PENDENTE
    elif chamado.status == StatusChamado.AGENDADO:
        dados_update_chamado['status'] = StatusChamado.EM_ATENDIMENTO

    # repo.update(chamado_id, dados_update_chamado)
    if dados_update_chamado:
        repo.update_chamado(chamado_id, dados_update_chamado)

    # return Visita(**visita_data)
    return visita_db


def _find_visit(chamado: dict, visita_id: int) -> tuple[int, dict]:
    visita_para_atualizar = None
    visita_index = -1
    for index, visita in enumerate(chamado.get('visitas', [])):
        if visita.get('id') == visita_id:
            visita_para_atualizar = visita
            visita_index = index
            break

    if not visita_para_atualizar:
        raise HTTPException(status_code=404, detail=f"Visita com ID {visita_id} não encontrada neste chamado.")
    return visita_index, visita_para_atualizar


@router.patch("/{chamado_id}/visitas/{visita_id}", response_model=Visita)
def update_visita_em_chamado(
        chamado_id: int,
        visita_id: int,
        visita_in: VisitaUpdate,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    """
    Atualiza os dados de uma visita específica.
    Permite ao técnico corrigir campos preenchidos de forma incorreta como KM, materiais, descrição, etc.
    """

    # chamado = repo.get_by_id(chamado_id)
    chamado = repo.get_chamado_by_id(chamado_id)
    # if not chamado or chamado.get('is_cancelled', False):
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado")

    logged_user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    # if user_role == "tecnico" and chamado.get('id_tecnico_atribuido') != logged_user_id:
    if user_role == "tecnico" and chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar visitas deste chamado.")

    # visita_index, visita_para_atualizar = _find_visit(chamado, visita_id)
    visita_db = repo.get_visita_by_id(visita_id)
    if not visita_db or visita_db.id_os != chamado_id:
        raise HTTPException(status_code=404, detail=f"Visita com ID {visita_id} não encontrada neste chamado.")

    update_data = visita_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar foi fornecido.")

    # visita_atualizada_dict = deep_update(visita_para_atualizar.copy(), update_data)
    visita_atualizada_dict = deep_update(visita_db.__dict__, update_data)
    if visita_atualizada_dict.get('servico_finalizado') is True:
        if not visita_atualizada_dict.get('assinatura_cliente_url'):
            raise HTTPException(status_code=400, detail="Assinatura do cliente é obrigatória para finalizar a visita.")

        if visita_atualizada_dict.get('km_total', 0) > 0:
            if not visita_atualizada_dict.get('odometro_inicio_url') or not visita_atualizada_dict.get(
                    'odometro_fim_url'):
                raise HTTPException(status_code=400,
                                    detail="Fotos do odômetro de início e fim são obrigatórias se km_total > 0.")

        if visita_atualizada_dict.get('valor_pedagio', 0.0) > 0:
            if not visita_atualizada_dict.get('comprovante_pedagio_urls'):
                raise HTTPException(status_code=400,
                                    detail="Comprovante(s) de pedágio são obrigatórios se valor_pedagio > 0.")

        if visita_atualizada_dict.get('valor_frete_devolucao', 0.0) > 0:
            if not visita_atualizada_dict.get('comprovante_frete_urls'):
                raise HTTPException(status_code=400,
                                    detail="Comprovante(s) de frete são obrigatórios se valor_frete_devolucao > 0.")

        # dados_update_chamado = {"status": "Finalizado", "data_conclusao": date.today()}
        # repo.update(chamado_id, dados_update_chamado)
        repo.update_chamado(chamado_id, {"status": StatusChamado.FINALIZADO, "data_conclusao": date.today()})

    elif visita_atualizada_dict.get('servico_finalizado') is False:
        pendencia = visita_atualizada_dict.get('pendencia')
        # dados_update_chamado = {
        #     "status": "Pendente" if pendencia else "Em Atendimento",
        #     "data_conclusao": None
        # }
        # repo.update(chamado_id, dados_update_chamado)
        repo.update_chamado(chamado_id, {
            "status": StatusChamado.PENDENTE if pendencia else StatusChamado.EM_ATENDIMENTO,
            "data_conclusao": None
        })

    # chamado['visitas'][visita_index] = visita_atualizada_dict
    # repo.update(chamado_id, {"visitas": chamado['visitas']})
    updated_visita = repo.update_visita(visita_id, update_data)
    if updated_visita is None:
        raise HTTPException(status_code=404, detail="Erro ao atualizar visita.")

    # return Visita(**visita_atualizada_dict)
    return updated_visita


@router.post("/{chamado_id}/iniciar-atendimento", response_model=Chamado)
def tecnico_inicia_atendimento(
        chamado_id: int,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(require_technician_role)
):
    """
    Valida se o chamado pertence ao técnico logado e altera o status de um chamado para 'Em Atendimento'.
    """
    logged_user_id = current_user.get("user_id")

    # chamado = repo.get_by_id(chamado_id)
    chamado = repo.get_chamado_by_id(chamado_id)
    # if not chamado or chamado.get('is_cancelled', False):
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado")

    # if chamado.get('id_tecnico_atribuido') != logged_user_id:
    if chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para iniciar este chamado.")

    # if chamado.get('status') not in ["Agendado", "Pendente"]:
    if chamado.status not in [StatusChamado.AGENDADO, StatusChamado.PENDENTE]:
        raise HTTPException(status_code=400,
                            detail=f"Não é possível iniciar um chamado com status '{chamado.status}'")

    # update_data = {"status": "Em Atendimento"}
    update_data = {"status": StatusChamado.EM_ATENDIMENTO}
    # updated_chamado = repo.update(chamado_id, update_data)
    updated_chamado = repo.update_chamado(chamado_id, update_data)

    # return Chamado(**updated_chamado)
    return updated_chamado


@router.get("/{chamado_id}/custos", response_model=CustoTotalResponse)
def get_custos_do_chamado(
        chamado_id: int,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    # chamado = repo.get_by_id(chamado_id)
    chamado = repo.get_chamado_by_id(chamado_id)
    # if not chamado or chamado.get('is_cancelled', False):
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    # id_tecnico_atribuido = chamado.get('id_tecnico_atribuido')

    # if user_role == "tecnico" and id_tecnico_atribuido != user_id:
    if user_role == "tecnico" and chamado.id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado aos custos deste chamado.")

    service = CustoService()
    chamado_dict = Chamado.model_validate(chamado).model_dump()
    # custos = service.calcular_custo_chamado(chamado)
    custos = service.calcular_custo_chamado(chamado_dict)
    return custos


@router.post("/{chamado_id}/visitas/{visita_id}/upload_file", response_model=Visita)
def upload_file_visita(
        chamado_id: int,
        visita_id: int,
        # repo: InMemoryRepository = Depends(get_chamado_repository),
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user),
        file: UploadFile = File(...),
        file_type: str = Form(..., description="Campo da visita para ser atualizado (URL do arquivo)."),
):
    """
    Permite o upload de um arquivo para uma visita específica, precisa de autenticação e autoria sobre o chamado.
    Se o campo file_type indicar uma lista, mais de uma foto poderá ser enviada (para casos de múltiplos comprovantes),
    caso contrário, o campo receberá uma única foto (sobrescreve a URL do arquivo já existente, sem apagar o mesmo).

    *OBS: Para enviar múltiplos arquivos, é necessário enviar UM por chamada. Múltiplos arquivos em uma única chamada serão ignorados.
    """

    logged_user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    # chamado = repo.get_by_id(chamado_id)
    chamado = repo.get_chamado_by_id(chamado_id)

    # if not chamado or chamado.get('is_cancelled', False):
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    # if user_role == "tecnico" and chamado.get('id_tecnico_atribuido') != logged_user_id:
    if user_role == "tecnico" and chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para este chamado.")

    # visita_index, visita_para_atualizar = _find_visit(chamado, visita_id)
    visita_db = repo.get_visita_by_id(visita_id)
    if not visita_db or visita_db.id_os != chamado_id:
        raise HTTPException(status_code=404, detail=f"Visita com ID {visita_id} não encontrada.")

    valid_fields = SINGLE_FILE_FIELDS + MULTI_FILE_FIELDS
    if file_type not in valid_fields:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo inválido: '{file_type}'.")

    prefixo_nome_arquivo = f"chamado_{chamado_id}_visita_{visita_id}_{file_type}"
    file_url = save_upload_file(file, prefixo_nome_arquivo)

    visita_para_atualizar = {}
    if file_type in SINGLE_FILE_FIELDS:
        # visita_para_atualizar[file_type] = file_url
        visita_para_atualizar[file_type] = file_url
    elif file_type in MULTI_FILE_FIELDS:
        # current_list = visita_para_atualizar.get(file_type, [])
        current_list = getattr(visita_db, file_type) or []
        if not isinstance(current_list, list): current_list = []
        current_list.append(file_url)
        visita_para_atualizar[file_type] = current_list

    # chamado['visitas'][visita_index] = visita_para_atualizar
    # repo.update(chamado_id, {"visitas": chamado['visitas']})

    visita_atualizada = repo.update_visita(visita_id, visita_para_atualizar)

    # return Visita(**visita_para_atualizar)
    return visita_atualizada
