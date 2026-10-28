# WorkManagement

Open task engine: admin workflows/types, tasks, attachments, entity links.

Notifications live in **[`../notify/`](../notify/)**. Work only emits `TaskAssigned`; it does not import notify.

## Folder map

| Folder | Contains |
| --- | --- |
| [`src/work/domain/`](src/work/domain/) | Task aggregate + events |
| [`src/work/application/`](src/work/application/) | WorkService |
| [`src/work/api/`](src/work/api/) | Task/workflow HTTP |
| [`src/work/database/`](src/work/database/) | `work_*` task tables |
| [`tests/`](tests/) | Pytest (run via `backend/core`: `uv run pytest`) |

## Permissions

`work:read|create|update|transition|attach|admin` (seeded in core).
