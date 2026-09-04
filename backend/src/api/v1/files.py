from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_file_service
from src.core.db import get_session
from src.schemas.files import FileItem, FileUpdate
from src.services.files import FileService
from src.worker.tasks import process_file

router = APIRouter(tags=["files"])


@router.get("/files", response_model=list[FileItem])
async def list_files(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: FileService = Depends(get_file_service),
):
    return await service.list(limit=limit, offset=offset)


@router.post("/files", response_model=FileItem, status_code=201)
async def create_file(
    background: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_session),
):
    item = await service.create(title=title, upload_file=file)
    # Коммит обязателен здесь, а не в фазе очистки get_session: без него
    # server_default-поля (created_at, updated_at, requires_attention) не
    # заполнены на момент сериализации ответа, и воркер не увидит строку.
    await session.commit()
    background.add_task(process_file.delay, item.id)
    return item


@router.get("/files/{file_id}", response_model=FileItem)
async def get_file(file_id: str, service: FileService = Depends(get_file_service)):
    return await service.get(file_id)


@router.patch("/files/{file_id}", response_model=FileItem)
async def update_file(
    file_id: str,
    payload: FileUpdate,
    service: FileService = Depends(get_file_service),
):
    return await service.rename(file_id=file_id, title=payload.title)


@router.get("/files/{file_id}/download")
async def download_file(file_id: str, service: FileService = Depends(get_file_service)):
    item, path = await service.path_for_download(file_id)
    return FileResponse(path=path, media_type=item.mime_type, filename=item.original_name)


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_session),
):
    await service.remove(file_id)
    # Тот же приём, что и в create_file: коммит здесь, а не в фазе очистки
    # get_session. Тот cleanup-коммит регистрируется в request-уровневом
    # AsyncExitStack и по факту выполняется ПОСЛЕ отправки ответа клиенту
    # (см. fastapi/routing.py: request_stack закрывается после
    # `await response(...)`). На быстром соединении клиент успевает
    # прислать следующий GET раньше, чем транзакция закоммитится, и видит
    # ещё не удалённую запись. Явный коммит до return убирает эту гонку.
    await session.commit()
