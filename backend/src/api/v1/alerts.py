from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.domain.models import Alert
from src.repositories.alerts import AlertRepository
from src.schemas.alerts import AlertItem

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertItem])
async def list_alerts(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Alert]:
    return await AlertRepository(session).list(limit=limit, offset=offset)
