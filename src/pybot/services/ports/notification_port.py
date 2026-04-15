from abc import ABC, abstractmethod

from ...dto import NotifyDTO


class NotificationPort(ABC):
    """Outbound notifications contract for application services.

    Notes:
        ``recipient_id`` semantics are transport-specific. In Telegram adapters
        this maps to ``telegram_id``/``chat_id``.
    """

    @abstractmethod
    async def send_role_request_to_admin(
        self,
        request_id: int,
        requester_user_id: int,
        role_name: str,
    ) -> None:
        """Send a role request notification to the administrator.

        Args:
            request_id: Unique role-request identifier.
            requester_user_id: Requester identifier in current notification
                transport semantics.
            role_name: Requested role name.

        Raises:
            NotificationTemporaryError: Transient delivery error, retry is allowed.
            NotificationPermanentError: Non-retryable delivery error.
        """
        pass

    @abstractmethod
    async def send_message(self, message_data: NotifyDTO) -> None:
        """Send a direct message to a single recipient.

        Args:
            message_data: Validated notification payload with recipient id and
                optional parse mode.

        Raises:
            NotificationTemporaryError: Transient delivery error, retry is allowed.
            NotificationPermanentError: Non-retryable delivery error.
        """
        pass
