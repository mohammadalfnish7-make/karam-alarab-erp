```
id: QA-FILE-001
title: Admin registers a file and finds it by name
module: identity
role: admin
locale: en
priority: major
type: happy
```

## Preconditions

- User: seeded admin
- API running with the upload directory writable

## Steps

1. Sign in as admin.
2. `POST /files` with a PDF named `Invoice-12.pdf`.
3. `GET /files?name=invoice`.
4. `GET /files/{id}/content`.
5. Repeat the search as a sales user.

## Expected

- Step 2 returns 201 and a display name of `Invoice-12.pdf`. The response has no storage key.
- Step 3 returns that file. A name that matches nothing returns an empty page.
- Step 4 downloads the same bytes with `Content-Disposition: attachment`.
- Sales receives 403 on search and upload.

## Actual

-

## Result

pass / fail / blocked

## Notes

Automated by `backend/filemanager/tests/test_files_api.py`.
