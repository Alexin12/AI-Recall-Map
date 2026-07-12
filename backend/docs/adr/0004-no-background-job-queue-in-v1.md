# No background job queue in V1

Extraction runs synchronously inside the FastAPI request, streaming progress back over the HTTP response, instead of being queued to a background worker. Pasted text — V1's only input — is small enough that in-request processing stays fast. Revisit when PDF or other large-file input arrives and extraction time grows past what a single request can hold open.

**Status**: accepted
