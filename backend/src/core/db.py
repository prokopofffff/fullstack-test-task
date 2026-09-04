from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

engine = create_async_engine(settings.db_url, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Одна сессия на запрос. Коммит — ответственность маршрута.

    Здесь намеренно нет commit(): зависимость завершается уже ПОСЛЕ того, как
    ответ отправлен клиенту, поэтому коммит в фазе очистки создаёт гонку —
    следующий запрос может обогнать запись. Маршрут, который что-то меняет,
    обязан закоммитить сам; забытый коммит откатится и сразу проявится в тестах,
    что куда лучше плавающей гонки.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
