from __future__ import annotations

from dishka.integrations.taskiq import FromDishka, inject

from ....core import logger
from ....dto import NotificationTaskPayload, NotifyDTO
from ....services.ports import NotificationPermanentError, NotificationPort, NotificationTemporaryError
from ..taskiq_app import get_taskiq_broker

broker = get_taskiq_broker()


@broker.task(task_name="notification.send_notification_task")
@inject(patch_module=True)
async def send_notification_task(
    notification_data: NotifyDTO,
    *,
    notification_port: FromDishka[NotificationPort],
) -> NotificationTaskPayload:
    """Отправить уведомление через настроенный notification port."""
    user_id, message = notification_data.user_id, notification_data.message

    try:
        logger.info("событие=отправка_уведомления status=started user_id={user_id}", user_id=user_id)
        await notification_port.send_message(notification_data)
        logger.info("событие=отправка_уведомления status=sent user_id={user_id}", user_id=user_id)
    except NotificationTemporaryError:
        logger.warning("событие=отправка_уведомления status=failed_temporary user_id={user_id}", user_id=user_id)
        return NotificationTaskPayload(status="failed_temporary", user_id=user_id, message=message)
    except NotificationPermanentError:
        logger.warning("событие=отправка_уведомления status=failed_permanent user_id={user_id}", user_id=user_id)
        return NotificationTaskPayload(status="failed_permanent", user_id=user_id, message=message)
    else:
        return NotificationTaskPayload(status="sent", user_id=user_id, message=message)
