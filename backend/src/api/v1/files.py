from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_file_service
from src.core.db import get_session
from src.schemas.files import FileItem, FileUpdate
from src.services.files import FileService
from src.tasks import scan_file_for_threats

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
    title: str = Form(...),
    file: UploadFile = File(...),
    service: FileService = Depends(get_file_service),
    session: AsyncSession = Depends(get_session),
):
    item = await service.create(title=title, upload_file=file)
    # get_session() commits only after the response has already been sent
    # (FastAPI runs yield-dependency cleanup post-response), but the worker
    # can pick up the queued task faster than that and find no row. Commit
    # explicitly here so the row is durable and visible before the task is
    # enqueued. Task 9 moves dispatch to BackgroundTasks, which runs after
    # dependency cleanup, so this explicit commit becomes unnecessary then.
    await session.commit()
    scan_file_for_threats.delay(item.id)
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
async def delete_file(file_id: str, service: FileService = Depends(get_file_service)):
    await service.remove(file_id)
