from abc import ABC, abstractmethod

from ...dto.value_objects import TaskSchedule


class NotificationDispatchPort(ABC):
    """Contract for dispatching notifications via background runtime."""

    @abstractmethod
    async def dispatch_message(
        self,
        recipient_id: int,
        message_text: str,
        schedule: TaskSchedule,
        parse_mode: str | None = None,
    ) -> str:
        """Dispatch a notification according to the provided schedule.

        Args:
            recipient_id: Recipient identifier in transport semantics.
            message_text: Notification text.
            schedule: Scheduling settings for delivery.
            parse_mode: Optional transport parse mode. When ``None``, adapters
                must omit it in transport calls.

        Returns:
            Task identifier for the queued/scheduled notification.
        """
        pass
