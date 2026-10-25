# COSMOW Phase 3 — RAG Prerequisite Audit

## Findings

- PostgreSQL connection succeeded against the currently configured Supabase database.
- Server version reported: PostgreSQL 17.11.
- The pgvector extension is enabled in that database; version 0.8.2.
- The backend virtual environment has pgvector Python package version 0.5.1.
- The document_chunks embedding column currently uses nullable JSON storage.
- The checked document_chunks table contains zero rows.
- The Alembic revision recorded in the checked database is fdaa4ad5b70a.
- Existing retrieval calculates cosine similarity in Python.

## Engineering decision

Evaluate migration to native PostgreSQL vector storage and database-side similarity search.

Before any schema modification:
- Confirm the intended database target.
- Review existing models, migrations, constraints, and tests.
- Preserve document ownership filters and existing data.
- Verify free-tier resource limits before selecting an index strategy.
- Test changes against an explicitly verified development/test database.

## Safety constraints

- No schema changes were made during this audit.
- No paid model fallback or billing upgrade is permitted.
- Do not assume the hosted database is disposable.
- Do not run migrations until the target database is verified.
