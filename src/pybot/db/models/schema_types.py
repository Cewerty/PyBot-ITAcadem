from sqlalchemy.dialects.postgresql import ENUM

from ...core.constants import PointsTypeEnum, RequestStatus, RoleEventOperandEnum

POINTS_TYPE_ENUM = ENUM(PointsTypeEnum, name="points_type_enum")
REQUEST_STATUS_ENUM = ENUM(RequestStatus, name="request_status_enum")
ROLE_EVENT_OPERAND_ENUM = ENUM(RoleEventOperandEnum, name="role_event_operand_enum")
