"""All SQLAlchemy table models — import this package to register metadata."""

from database.models.audit import AuditEntryRow
from database.models.identity import (
    LoginAttemptRow,
    PermissionRow,
    RolePermissionRow,
    RoleRow,
    SessionRow,
    UserRoleRow,
    UserRow,
)
from database.models.work import (
    NotificationChannelRow,
    NotificationRow,
    TaskAttachmentRow,
    TaskCommentRow,
    TaskEntityLinkRow,
    TaskLinkRow,
    TaskRow,
    TaskStepRow,
    TaskTypeRow,
    WebhookDeliveryRow,
    WorkflowRow,
    WorkflowStatusRow,
    WorkflowTransitionRow,
)

__all__ = [
    "AuditEntryRow",
    "LoginAttemptRow",
    "NotificationChannelRow",
    "NotificationRow",
    "PermissionRow",
    "RolePermissionRow",
    "RoleRow",
    "SessionRow",
    "TaskAttachmentRow",
    "TaskCommentRow",
    "TaskEntityLinkRow",
    "TaskLinkRow",
    "TaskRow",
    "TaskStepRow",
    "TaskTypeRow",
    "UserRoleRow",
    "UserRow",
    "WebhookDeliveryRow",
    "WorkflowRow",
    "WorkflowStatusRow",
    "WorkflowTransitionRow",
]
