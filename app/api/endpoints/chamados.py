from fastapi import APIRouter, Depends, HTTPException, Query, Response, File, UploadFile, Form
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, require_admin_role, require_technician_role
from app.db.database import get_db
from app.repositories.mysql_repository import SQLRepository
from app.schemas.chamado import Chamado, ChamadoCreate, ChamadoUpdate, StatusChamado
from app.schemas.visita import Visita, VisitaCreate, VisitaUpdate
from app.schemas.custo import CustoTotalResponse
from app.services.custo_service import CustoService
from app.services.file_service import save_upload_file

router = APIRouter()
MULTI_FILE_FIELDS = ["comprovante_pedagio_urls", "comprovante_frete_urls"]
SINGLE_FILE_FIELDS = ["odometro_inicio_url", "odometro_fim_url", "assinatura_cliente_url"]


def get_chamado_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


def get_cliente_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


def get_tecnico_repository(db: Session = Depends(get_db)):
    return SQLRepository(db=db)


@router.post("/", response_model=Chamado, status_code=201)
def create_chamado(
        chamado_in: ChamadoCreate,
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
    chamado_data['is_cancelled'] = False

    if chamado_data.get('id_tecnico_atribuido') is not None:
        chamado_data['status'] = StatusChamado.AGENDADO
    else:
        chamado_data['status'] = StatusChamado.ABERTO

    chamado_criado_db = repo.create_chamado(chamado_data)
    return chamado_criado_db


@router.get("/", response_model=List[Chamado])
def get_todos_chamados(
        repo: SQLRepository = Depends(get_chamado_repository),
        is_cancelled: Optional[bool] = Query(None, description="Filtra chamados pelo status de cancelamento"),
        current_user: dict = Depends(get_current_active_user)
):
    chamados_list_db = repo.get_chamados()
    response_list = []
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    for chamado_db in chamados_list_db:
        is_chamado_cancelado = chamado_db.is_cancelled
        id_tecnico_atribuido = chamado_db.id_tecnico_atribuido

        if is_cancelled is not None and is_chamado_cancelado != is_cancelled:
            continue

        if user_role == "tecnico":
            if id_tecnico_atribuido != user_id:
                continue

        response_list.append(chamado_db)

    return response_list


@router.get("/{chamado_id}", response_model=Chamado)
def get_chamado_por_id(
        chamado_id: int,
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    chamado_encontrado = repo.get_chamado_by_id(chamado_id)
    if not chamado_encontrado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    if user_role == "tecnico" and chamado_encontrado.id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado a este chamado.")

    return chamado_encontrado


@router.patch("/{chamado_id}", response_model=Chamado)
def update_chamado(
        chamado_id: int,
        chamado_in: ChamadoUpdate,
        repo: SQLRepository = Depends(get_chamado_repository),
        tecnico_repo: SQLRepository = Depends(get_tecnico_repository),
        current_user: dict = Depends(get_current_active_user)
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

    updated_chamado = repo.update_chamado(chamado_id, update_data)
    if updated_chamado is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")

    return updated_chamado


@router.delete("/{chamado_id}", status_code=204)
def delete_chamado(
        chamado_id: int,
        repo: SQLRepository = Depends(get_chamado_repository),
        _admin_user: dict = Depends(require_admin_role)
):
    success = repo.delete_chamado(chamado_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    return Response(status_code=204)


@router.post("/{chamado_id}/visitas", response_model=Visita, status_code=201)
def add_visita_ao_chamado(
        chamado_id: int,
        visita_in: VisitaCreate,
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user),
):
    """
    Adiciona uma nova visita ao chamado.
    Requer que o usuário esteja autenticado com um token JWT válido
    """
    logged_user_id = current_user["user_id"]

    chamado = repo.get_chamado_by_id(chamado_id)
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if chamado.id_tecnico_atribuido != logged_user_id:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403,
                                detail="Você não tem permissão para adicionar uma visita neste chamado.")

    if visita_in.servico_finalizado:
        raise HTTPException(status_code=400,
                            detail="Não é possível criar uma visita já finalizada. Crie a visita, faça os uploads e depois finalize-a.")

    visita_data = visita_in.model_dump()
    visita_db = repo.create_visita(chamado_id, visita_data)

    dados_update_chamado = {}
    if visita_in.pendencia:
        dados_update_chamado['status'] = StatusChamado.PENDENTE
    elif chamado.status == StatusChamado.AGENDADO:
        dados_update_chamado['status'] = StatusChamado.EM_ATENDIMENTO

    if dados_update_chamado:
        repo.update_chamado(chamado_id, dados_update_chamado)

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
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    """
    Valida as regras de negócio para finalização e atualiza o status do chamado pai.
    Permite ao técnico corrigir campos preenchidos de forma incorreta como KM, materiais, descrição, etc.
    """
    chamado = repo.get_chamado_by_id(chamado_id)
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado")

    logged_user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    if user_role == "tecnico" and chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar visitas deste chamado.")

    updated_visita = repo.update_visita_e_chamado(visita_id, chamado_id, visita_in)
    if updated_visita is None:
        raise HTTPException(status_code=404, detail="Erro ao atualizar visita.")

    return updated_visita


@router.post("/{chamado_id}/iniciar-atendimento", response_model=Chamado)
def tecnico_inicia_atendimento(
        chamado_id: int,
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(require_technician_role)
):
    """
    Valida se o chamado pertence ao técnico logado e altera o status de um chamado para 'Em Atendimento'.
    """
    logged_user_id = current_user.get("user_id")

    chamado = repo.get_chamado_by_id(chamado_id)
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado")

    if chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para iniciar este chamado.")

    if chamado.status not in [StatusChamado.AGENDADO, StatusChamado.PENDENTE]:
        raise HTTPException(status_code=400,
                            detail=f"Não é possível iniciar um chamado com status '{chamado.status}'")

    update_data = {"status": StatusChamado.EM_ATENDIMENTO}
    updated_chamado = repo.update_chamado(chamado_id, update_data)

    return updated_chamado


@router.get("/{chamado_id}/custos", response_model=CustoTotalResponse)
def get_custos_do_chamado(
        chamado_id: int,
        repo: SQLRepository = Depends(get_chamado_repository),
        current_user: dict = Depends(get_current_active_user)
):
    chamado = repo.get_chamado_by_id(chamado_id)
    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    if user_role == "tecnico" and chamado.id_tecnico_atribuido != user_id:
        raise HTTPException(status_code=403, detail="Acesso negado aos custos deste chamado.")

    service = CustoService()
    chamado_dict = Chamado.model_validate(chamado).model_dump()
    custos = service.calcular_custo_chamado(chamado_dict)
    return custos


@router.post("/{chamado_id}/visitas/{visita_id}/upload_file", response_model=Visita)
def upload_file_visita(
        chamado_id: int,
        visita_id: int,
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
    chamado = repo.get_chamado_by_id(chamado_id)

    if not chamado or chamado.is_cancelled:
        raise HTTPException(status_code=404, detail="Chamado não encontrado ou cancelado.")

    if user_role == "tecnico" and chamado.id_tecnico_atribuido != logged_user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para este chamado.")

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
        visita_para_atualizar[file_type] = file_url
    elif file_type in MULTI_FILE_FIELDS:
        current_list = getattr(visita_db, file_type) or []
        if not isinstance(current_list, list): current_list = []
        current_list.append(file_url)
        visita_para_atualizar[file_type] = current_list

    visita_atualizada = repo.update_visita(visita_id, visita_para_atualizar)
    return visita_atualizada
