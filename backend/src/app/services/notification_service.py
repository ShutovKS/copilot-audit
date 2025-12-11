import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.app.domain.models import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    async def create_notification(
        self,
        db: AsyncSession,
        session_id: str,
        message: str,
        related_run_id: int | None = None,
    ):
        """Creates and saves a new notification."""
        logger.info(f"Creating notification for session {session_id[:6]}: {message}")
        notification = Notification(
            session_id=session_id,
            message=message,
            related_run_id=related_run_id
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification
