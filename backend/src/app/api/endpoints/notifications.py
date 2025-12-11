import logging
from typing import Annotated  # Added Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.api.models import NotificationSchema
from src.app.core.database import get_db
from src.app.domain.models import Notification

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[NotificationSchema])
async def get_notifications(
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID"),
		unread_only: bool = True,
):
	"""
	Get all notifications for the current session.
	"""
	query = select(Notification).where(Notification.session_id == x_session_id)
	if unread_only:
		query = query.where(not Notification.is_read)

	result = await db.execute(query.order_by(Notification.created_at.desc()))
	notifications = result.scalars().all()
	return notifications


@router.post("/{notification_id}/read", response_model=NotificationSchema)
async def mark_notification_as_read(
		notification_id: int,
		db: Annotated[AsyncSession, Depends(get_db)],
		x_session_id: str = Header(..., alias="X-Session-ID"),
):
	"""
	Mark a specific notification as read.
	"""
	result = await db.execute(
		select(Notification).where(
			Notification.id == notification_id,
			Notification.session_id == x_session_id
		)
	)
	notification = result.scalars().first()

	if not notification:
		raise HTTPException(status_code=404, detail="Notification not found")

	notification.is_read = True
	await db.commit()
	await db.refresh(notification)
	return notification
