# Phase 4 ops queries (no admin UI)

## Failed ingestions

```sql
SELECT id, document_id, status, stage, error_code, error_message, created_at
FROM ingestion_jobs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 50;
```

## Recent eval runs

```sql
SELECT id, dataset_version, status, sample_count, aggregate_metrics, created_at, finished_at
FROM eval_runs
ORDER BY created_at DESC
LIMIT 20;
```

## Tenant corpus versions

```sql
SELECT id, email, corpus_version, updated_at
FROM users
ORDER BY corpus_version DESC
LIMIT 50;
```
