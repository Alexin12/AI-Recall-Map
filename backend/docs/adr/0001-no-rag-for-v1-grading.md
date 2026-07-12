# No RAG for V1 grading

Grading needs no retrieval: each Concept stores its own source snippet, and the grading prompt is built from the Concept's explanation + that snippet + the user's answer. OpenAI File Search was considered for retrieval speed and rejected — retrieval adds a round trip and latency, not speed, and keeping all data in Supabase (rather than a second vector store) matches the privacy promise. RAG only becomes relevant later, when the app needs to search across many saved Materials — then pgvector, not File Search.

**Status**: accepted
