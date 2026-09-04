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
    # get_session больше не коммитит сам (см. src/core/db.py) — коммит здесь
    # обязателен: без него ничего не попадёт в БД, а server_default-поля
    # (created_at, updated_at, requires_attention) не заполнены на момент
    # сериализации ответа, и воркер не увидит строку.
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
    session: AsyncSession = Depends(get_session),
):
    item = await service.rename(file_id=file_id, title=payload.title)
    # Тот же приём, что и в create_file/delete_file: get_session больше не
    # коммитит в фазе очистки, поэтому маршрут обязан сделать это сам, до
    # возврата ответа — иначе следующий быстрый GET может обогнать запись.
    await session.commit()
    # updated_at считается на стороне БД (onupdate=func.now()), и после
    # UPDATE SQLAlchemy помечает это поле как требующее перечитывания даже
    # при expire_on_commit=False. Без явного refresh сериализация ответа
    # (она идёт вне async-контекста) падает с MissingGreenlet при попытке
    # лениво подгрузить значение.
    await session.refresh(item)
    return item


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
    # get_session больше не коммитит сам (см. src/core/db.py) — коммит здесь
    # обязателен, иначе удаление откатится при закрытии сессии и клиент
    # получит 204, хотя запись осталась на месте.
    await session.commit()
