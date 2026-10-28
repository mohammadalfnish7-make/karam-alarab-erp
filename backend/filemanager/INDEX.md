# File catalog

Shared file metadata and a local blob folder. Work, Freight, and Warehouse keep a file id. They do not import this package.

Bytes live in `{upload_dir}/catalog` under a random key. The display name is only in `file_catalog_files`.

## Folder map

| Folder | Contains |
| --- | --- |
| [`src/filemanager/domain/`](src/filemanager/domain/) | `StoredFile` aggregate, type checks |
| [`src/filemanager/application/`](src/filemanager/application/) | `FileService` (`FileCatalog` port) |
| [`src/filemanager/api/`](src/filemanager/api/) | `/files` HTTP |
| [`src/filemanager/storage/`](src/filemanager/storage/) | Local blob folder |
| [`src/filemanager/database/`](src/filemanager/database/) | `file_catalog_files` |

## HTTP

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/files` | `files:write` |
| GET | `/files?name=` | `files:read` |
| GET | `/files/{id}` | `files:read` |
| GET | `/files/{id}/content` | `files:read` |

`main.py` mounts the router and subscribes `FileRegistered` to the audit log. Modules call `get_file_catalog` from core when they need a file id. Task attachments are unchanged.

## Permissions

`files:read` and `files:write`. Seeded for admin. Operations and warehouse get both. Support gets read. Sales gets neither.
