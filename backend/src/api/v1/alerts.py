from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import Pagination, get_pagination
from src.core.db import get_session
from src.domain.models import Alert
from src.repositories.alerts import AlertRepository
from src.schemas.alerts import AlertItem

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertItem])
async def list_alerts(
    pagination: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_session),
) -> list[Alert]:
    return await AlertRepository(session).list(limit=pagination.limit, offset=pagination.offset)
