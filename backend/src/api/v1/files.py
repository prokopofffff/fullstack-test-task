from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from src.api.deps import Pagination, get_file_service, get_pagination
from src.domain.models import StoredFile
from src.schemas.files import FileItem, FileUpdate
from src.services.files import FileService
from src.worker.tasks import process_file

router = APIRouter(tags=["files"])


@router.get("/files", response_model=list[FileItem])
async def list_files(
    pagination: Pagination = Depends(get_pagination),
    service: FileService = Depends(get_file_service),
) -> list[StoredFile]:
    return await service.list(limit=pagination.limit, offset=pagination.offset)


@router.post("/files", response_model=FileItem, status_code=201)
async def create_file(
    background: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    service: FileService = Depends(get_file_service),
) -> StoredFile:
    # FileService.create сам коммитит (unit of work — см. src/services/files.py),
    # поэтому к моменту возврата запись уже видна снаружи, и process_file
    # можно смело ставить в очередь.
    item = await service.create(title=title, upload_file=file)
    background.add_task(process_file.delay, item.id)
    return item


@router.get("/files/{file_id}", response_model=FileItem)
async def get_file(file_id: str, service: FileService = Depends(get_file_service)) -> StoredFile:
    return await service.get(file_id)


@router.patch("/files/{file_id}", response_model=FileItem)
async def update_file(
    file_id: str,
    payload: FileUpdate,
    service: FileService = Depends(get_file_service),
) -> StoredFile:
    # FileService.rename сам коммитит и делает refresh (см. src/services/files.py).
    return await service.rename(file_id=file_id, title=payload.title)


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str, service: FileService = Depends(get_file_service)
) -> FileResponse:
    item, path = await service.path_for_download(file_id)
    return FileResponse(path=path, media_type=item.mime_type, filename=item.original_name)


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
) -> None:
    # FileService.remove сам коммитит (см. src/services/files.py).
    await service.remove(file_id)
