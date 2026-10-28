# Notifications

Inbox + admin webhook channels + durable delivery worker.

Owns delivery; does **not** own task assign. Work emits `TaskAssigned`; the composition root (`core/src/main.py`) adapts it to `AssignNotifyCommand`. **Notify imports core only** — never `work`.

## Folder map

| Folder | Contains |
| --- | --- |
| [`src/notify/domain/`](src/notify/domain/) | Webhook signing + SSRF URL rules |
| [`src/notify/application/`](src/notify/application/) | ChannelService, NotifyListener, delivery worker |
| [`src/notify/api/`](src/notify/api/) | Channels, inbox, `POST /work/process-deliveries` |
| [`src/notify/database/`](src/notify/database/) | Tables still named `work_notification*` / `work_webhook_deliveries` |

## Permissions

Channel admin still uses `work:admin` (unchanged HTTP behavior). Inbox uses the authenticated user.
