# COSMOW Phase 3 — Vector Migration Design

## Objective

Move RAG embedding storage and similarity ranking from JSON/Python
processing to PostgreSQL native vector storage and database-side
similarity search, while preserving access control and free-tier limits.

## Verified starting point

- PostgreSQL 17.11 was reported by the currently configured Supabase database.
- The vector extension was enabled there at version 0.8.2.
- The backend virtual environment has pgvector Python package version 0.5.1.
- The document_chunks.embedding column is nullable JSON.
- The checked document_chunks table contained zero rows at audit time.
- The checked database Alembic revision was fdaa4ad5b70a.
- COSMOW configures embedding dimensions as 768.
- Existing retrieval calculates cosine similarity in Python.

These findings describe the database that was inspected. They do not
prove that the local database has identical data or schema.

## Proposed staged migration

1. Verify the intended local development/test database and its Alembic revision.
2. Review the existing model, migrations, retrieval service, and tests.
3. Add a nullable native vector column with dimension 768 while retaining JSON.
4. Backfill only embeddings that pass dimension and finite-number validation.
5. Test vector persistence and retrieval against an isolated test database.
6. Update retrieval to use PostgreSQL cosine distance and deterministic ordering.
7. Preserve user ownership and indexed-document filters in every query.
8. Compare results with the existing implementation using controlled test vectors.
9. Evaluate indexing only after correctness is established and resource limits are checked.
10. Remove the legacy JSON column only in a later reviewed migration, after confirming
    the new path works and a recovery strategy is available.

This sequence is a proposal, not an authorization to modify the hosted database.
The exact migration mechanics must be confirmed during implementation.

## Retrieval requirements

- Use the configured 768-dimensional embedding size.
- Reject invalid query vectors before executing a similarity query.
- Return only chunks belonging to the requesting user.
- Exclude documents that are not indexed or chunks without valid vectors.
- Order by cosine distance and use a stable tie-breaker.
- Keep result limits bounded.
- Avoid embedding documents or queries again when existing cached results suffice.

## Testing requirements

- Valid vector persistence and retrieval.
- Empty documents and missing embeddings.
- Wrong dimensions and non-finite vector values.
- Similarity ranking and deterministic ordering.
- Cross-user isolation.
- Exclusion of non-indexed documents.
- Transaction rollback when embedding or persistence fails.
- Migration upgrade and downgrade behavior on an isolated test database.
- Regression suite passes before each commit.

## Resource and cost controls

- No local model training.
- No paid model or hosting fallback.
- No automatic billing upgrades or auto-recharge.
- Stop provider requests when free-tier quota is unavailable.
- Keep test datasets small and result limits bounded.
- Do not create a vector index until its resource cost and suitability are reviewed.
- Do not run schema migrations against Supabase during local development.

## Rollback strategy

- Keep the JSON column during the transition.
- Verify backfill counts and vector validity before switching application reads.
- Keep changes in separate, reviewable commits.
- Test rollback against an isolated database before considering any hosted migration.
- Do not drop legacy storage until recovery and data preservation are verified.

## Acceptance criteria

- Migration behavior is tested against an explicitly verified test database.
- Existing ownership and indexing filters remain enforced.
- Similarity results are correct and deterministic for controlled fixtures.
- The full backend test suite passes.
- No real credentials or provider secrets enter the repository.
- Every completed phase step is committed and pushed only after review.
