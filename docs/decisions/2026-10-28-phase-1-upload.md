# ADR: Phase 1 upload and file scope

## Status

Accepted.

## Decisions

1. Supported upload types only: `.md`, `.markdown`, `.txt`, `.pdf`, `.csv`, `.docx`. No OCR, no `.doc`, no URL/Drive/Sheets/camera.
2. Object keys are server-generated: `users/{user_id}/documents/{document_id}/original`.
3. On upload complete: verify object size via HEAD, then commit `queued` document + ingestion job + outbox in one transaction.
4. Ingestion processing (parse/chunk/embed) starts in Phase 2; outbox may remain `pending` if Inngest dispatch fails.
5. Delete sets `deleting` immediately; finalize `deleted` when storage delete succeeds, otherwise leave retryable outbox.
6. Sample `items` table/API removed.
