# Recall Map Plan v2 - Option C: AI-First RAG and Knowledge Graph

## Positioning

Build Recall Map as an AI-first learning system:

1. Learners upload or paste learning materials.
2. The system turns them into a searchable personal knowledge base.
3. AI extracts concepts, questions, relationships, and review plans.
4. AI judges understanding using retrieved source evidence.
5. The concept map becomes the main navigation surface.

This version treats retrieval and concept relationships as core product features from the beginning.

## Best Fit

Choose this version if the main goal is to learn AI app architecture, retrieval, file search, embeddings, and knowledge graph design.

Do not choose this version if the main goal is to ship a simple useful app quickly.

## Core Scope

### In Scope

- Account sign-in.
- Paste text.
- Markdown upload.
- PDF upload.
- File storage.
- Chunking.
- Embeddings.
- Vector search.
- AI extraction.
- AI grading with retrieval.
- Concept graph.
- Review queue.
- Source-grounded feedback.
- Concept search.
- Multi-step AI workflows.

### Possible Later Scope

- Word documents.
- Google Docs.
- Image OCR.
- Excel.
- Browser extension.
- Public shared concept maps.
- Native mobile app.

## Recommended Stack

- Frontend and backend: Next.js 16 App Router.
- Language: TypeScript.
- UI: Tailwind CSS and shadcn/ui.
- Database: Supabase Postgres.
- Auth: Supabase Auth with `@supabase/ssr`.
- File storage: Supabase Storage.
- Vector storage option 1: Supabase pgvector.
- Vector storage option 2: OpenAI vector stores and File Search.
- AI orchestration: OpenAI Responses API.
- Structured generation: OpenAI Structured Outputs.
- Optional abstraction: AI SDK v6 for provider flexibility.
- Background jobs: Inngest or Trigger.dev.
- Deployment: Vercel.

Plain language: this version has an AI pipeline, not just an AI button. Uploading content starts background work, and different AI steps create different database records.

## Current API Notes

Checked on 2026-07-08:

- Next.js docs list 16.2.10 as the latest version and App Router as the newer router.
- AI SDK v6 is the latest AI SDK version and supports text, structured object generation, tools, embeddings, and UI helpers.
- OpenAI docs recommend Responses API for new text generation apps.
- OpenAI File Search is available as a Responses API tool and can search uploaded files through vector stores.
- OpenAI Structured Outputs should be used when generated data must match a JSON schema.
- Supabase supports vector columns through pgvector and can run similarity search through Postgres functions.

## Architecture Choice

This option has two possible retrieval designs.

### Design C1: Supabase-Owned Retrieval

Store chunks and embeddings in Supabase Postgres with pgvector.

Plain language:

The app owns the knowledge base. You can inspect and query everything in your database.

Pros:

- More control.
- Easier to debug.
- Easier to connect chunks to concepts, users, and review data.
- Good for building your own product logic.

Cons:

- You must implement chunking, embedding, search functions, and indexing.
- More backend work.
- More ways to make mistakes.

### Design C2: OpenAI-Hosted File Search

Upload files to OpenAI vector stores and use the `file_search` tool in Responses API calls.

Plain language:

OpenAI manages much of the retrieval work. The app asks the model to search the uploaded knowledge base.

Pros:

- Faster to build retrieval.
- Less custom search code.
- Good for source-grounded AI answers.

Cons:

- Less control over retrieval internals.
- Harder to fully inspect ranking behavior.
- You still need app tables for concepts, review items, and user progress.
- Vendor coupling is stronger.

## Recommendation

Use Supabase-owned retrieval for this project unless speed is more important than control.

Reason:

Recall Map is not only a chatbot over files. It needs concepts, relationships, review history, mastery state, and source references. Keeping retrieval data close to the product data makes the system easier to reason about.

## System Pipeline

### 1. Ingestion

Input:

- pasted text
- Markdown
- PDF

Output:

- material record
- extracted text
- chunks
- file metadata

### 2. Chunking

Split material into chunks with:

- chunk text
- chunk index
- approximate token count
- source location
- title path

Plain language:

Chunking means cutting a long lesson into smaller pieces so search and AI calls can focus on the relevant part.

### 3. Embedding

Generate an embedding for every chunk.

Output:

- vector stored in database

Plain language:

An embedding is a list of numbers that represents meaning. Similar ideas end up close together.

### 4. Concept Extraction

Run AI extraction over chunks or chunk groups.

Output:

- concepts
- questions
- relationships
- source chunk references

### 5. Concept Merge

Detect duplicate or similar concepts.

Example:

- "Dependency Injection"
- "DI"
- "Injecting dependencies"

These may become one canonical concept.

Plain language:

Without merging, the app may create three cards for the same idea.

### 6. Review Scheduling

Create review items for each approved concept.

Start with simple scheduling:

- fail: review today again
- partial: review tomorrow
- pass: review in 3 days
- strong pass: review in 7 days

### 7. Retrieval-Grounded Grading

When the learner answers:

1. Retrieve related source chunks.
2. Send the concept, question, expected answer, learner answer, and source chunks to AI.
3. Return structured feedback.

Plain language:

The AI should grade against the learner's own material, not only its general memory.

## Data Model

### profiles

- id
- email
- created_at

### collections

- id
- user_id
- name
- description
- created_at

### materials

- id
- user_id
- collection_id
- title
- source_type
- storage_path
- raw_text
- status
- error_message
- created_at

### material_chunks

- id
- user_id
- material_id
- chunk_index
- heading
- text
- token_count
- source_locator
- embedding
- created_at

### concepts

- id
- user_id
- collection_id
- canonical_name
- explanation
- analogy
- mastery_score
- confidence
- created_at

### concept_sources

- id
- user_id
- concept_id
- material_id
- chunk_id
- relevance

### concept_aliases

- id
- user_id
- concept_id
- alias

### concept_relationships

- id
- user_id
- collection_id
- from_concept_id
- to_concept_id
- relationship_type
- explanation
- confidence

### questions

- id
- user_id
- concept_id
- question_type
- prompt
- expected_answer
- rubric
- difficulty

### review_items

- id
- user_id
- concept_id
- due_at
- interval_days
- ease
- status
- last_result

### review_attempts

- id
- user_id
- review_item_id
- question_id
- answer
- result
- score
- missing_points
- feedback
- retrieved_chunk_ids
- created_at

### ai_runs

- id
- user_id
- run_type
- input_ref
- output_ref
- model
- status
- created_at

## UI Structure

### Dashboard

- due today
- weak concepts
- recently learned
- collections
- review streak

### Add Material

- paste text
- upload file
- ingestion status
- extraction status

### Collection Page

- materials
- concepts
- concept map
- search

### Concept Page

- explanation
- analogy
- source chunks
- linked concepts
- review history
- active recall questions

### Review Page

- one question at a time
- answer input
- feedback
- next concept

### Map Page

- graph of concepts
- filters
- mastery colors
- click node to open concept

## Implementation Steps

### Step 1: Product Skeleton

- Next.js app.
- Auth.
- Collections.
- Protected dashboard.

Validation:

- users can create collections
- row-level security prevents cross-user reads

### Step 2: Ingestion Foundation

- Paste text.
- Markdown upload.
- PDF text extraction.
- Supabase Storage.
- `materials` and `material_chunks`.

Validation:

- uploaded file becomes chunks
- failed ingestion is visible

### Step 3: Embeddings and Search

- Generate embeddings for chunks.
- Store vectors in Supabase.
- Add match function.
- Add semantic search UI.

Validation:

- paraphrase search finds the correct chunk

### Step 4: Concept Extraction

- Add extraction workflow.
- Use Structured Outputs.
- Store concepts, aliases, relationships, questions, and sources.

Validation:

- one lesson creates usable concepts
- concepts link back to source chunks

### Step 5: Merge and Approval

- Detect likely duplicate concepts.
- Let user approve, merge, edit, or delete.

Validation:

- duplicate concepts do not flood review queue

### Step 6: Review Engine

- Create review items.
- Add flashcard and written-answer modes.
- Save review attempts.

Validation:

- review queue changes after each attempt

### Step 7: Retrieval-Grounded Grading

- Retrieve relevant chunks for a concept and answer.
- Grade with AI.
- Store retrieved chunk IDs with the attempt.

Validation:

- feedback references the right source section

### Step 8: Concept Map

- Render graph.
- Filter by collection, time, and mastery.
- Open concept detail from graph node.

Validation:

- graph remains useful with 50 concepts

## Plain-Language Tradeoffs

### Pros

- Most powerful version.
- Best match for "Recall Map" as a knowledge system.
- Strongest AI learning experience.
- Source-grounded grading is more trustworthy.
- Good learning project for modern AI app architecture.

### Cons

- Highest complexity.
- More expensive to build and run.
- More background jobs.
- More edge cases.
- Harder to finish in one month.

## Main Risk

The system can become an ingestion and retrieval project before it becomes a useful review app.

Mitigation:

- Build review with pasted text first.
- Add PDF second.
- Add embeddings third.
- Keep every AI feature tied to one learner action.

## Success Criteria

- The app can ingest at least one real course lesson.
- The app can search by meaning, not only keywords.
- AI-generated concepts link back to source chunks.
- AI grading uses retrieved source material.
- Review history changes the learner's future queue.
- The concept map helps navigation instead of becoming decoration.

## Recommended First Build

Do not start here unless the purpose is specifically to learn RAG and AI pipelines.

If the purpose is to ship a usable product, start with Option A or Option B, then evolve toward this design.

## References

- Next.js docs: https://nextjs.org/docs
- Supabase SSR auth docs: https://supabase.com/docs/guides/auth/server-side/creating-a-client?queryGroups=framework&framework=nextjs
- Supabase vector columns docs: https://supabase.com/docs/guides/ai/vector-columns
- OpenAI Responses API text generation docs: https://developers.openai.com/api/docs/guides/text
- OpenAI File Search docs: https://developers.openai.com/api/docs/guides/tools-file-search
- OpenAI Structured Outputs docs: https://developers.openai.com/api/docs/guides/structured-outputs
- AI SDK docs: https://ai-sdk.dev/docs/introduction
