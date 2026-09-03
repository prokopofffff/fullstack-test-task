from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.domain.models import Alert
from src.schemas.alerts import AlertItem

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertItem])
async def list_alerts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Alert).order_by(Alert.created_at.desc()))
    return list(result.scalars().all())
