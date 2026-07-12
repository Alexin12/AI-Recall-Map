# Recall Map Plan v2 - Option B: Balanced Product MVP

## Positioning

Build a web app that feels like a real learning product, while still keeping the first version practical.

The core idea:

1. Learners add study material.
2. Recall Map extracts concepts, questions, analogies, and relationships.
3. The app builds a review queue.
4. Learners test themselves.
5. The app recommends what to review next.

This version supports more realistic inputs and a stronger review system than Option A.

## Best Fit

Choose this version if the goal is a polished portfolio product that can become a real app, but still needs to stay manageable.

## Core Scope

### In Scope

- Account sign-in.
- Paste text.
- Markdown upload.
- PDF upload with text extraction.
- Course or collection organization.
- AI concept extraction.
- AI question generation.
- AI answer judging.
- Review queue.
- Simple spaced repetition.
- Concept map.
- Search across saved concepts.
- Source links back to the original material section.

### Out of Scope

- Google Docs import.
- Word and Excel import.
- Image OCR.
- Complex graph database.
- Social features.
- Payments.
- Native mobile app.

## Recommended Stack

- Frontend and backend: Next.js 16 App Router.
- Language: TypeScript.
- UI: Tailwind CSS and shadcn/ui.
- Database: Supabase Postgres.
- Auth: Supabase Auth with `@supabase/ssr`.
- File storage: Supabase Storage.
- AI: OpenAI Responses API.
- Structured generation: OpenAI Structured Outputs.
- Embeddings and semantic search: Supabase Postgres with pgvector.
- Background work: Inngest, Trigger.dev, or Supabase Edge Functions later.
- Deployment: Vercel.

Plain language: this version adds enough backend structure that the app can grow, but it avoids the hardest ingestion types until the learning loop is proven.

## Current API Notes

Checked on 2026-07-08:

- Next.js 16 App Router is the default choice for a new full-stack React app.
- Supabase SSR auth uses `@supabase/ssr` and cookie-based clients for Next.js.
- Supabase Storage standard upload is simple for small files, while large files should use resumable upload.
- Supabase supports vector columns through pgvector for embeddings and similarity search.
- OpenAI Responses API is recommended over older Chat Completions for new text generation apps.
- OpenAI Structured Outputs should be used for extraction and grading schemas.

## Product Structure

### Workspace

A user owns one personal learning workspace.

### Collection

A collection is a course, book, topic, or learning area.

Examples:

- FastAPI Course
- JavaScript Basics
- AI Agent Notes

### Material

A material is one uploaded or pasted learning source.

Examples:

- one lesson transcript
- one article
- one PDF chapter
- one Markdown note

### Concept

A concept is one idea the learner should understand and remember.

### Review Item

A review item is a scheduled future test for one concept.

## User Flow

### 1. Add Material

User chooses:

- collection
- input type
- title
- paste text or upload file

System:

- stores the original material
- extracts text
- splits text into chunks
- generates concepts and questions
- saves source references

### 2. Learn Page

After ingestion, the learner sees:

- extracted concepts
- short explanations
- analogies
- relationships
- suggested questions

The learner can approve, edit, or delete generated concepts.

Plain language: AI output should not silently become truth. The learner should be able to fix bad concepts before they pollute the review system.

### 3. Review Page

The learner sees:

- due today
- weak concepts
- recently learned
- by collection
- by time period

Review modes:

- flashcard
- explain in your own words
- compare two concepts
- connect concepts

### 4. AI Feedback

For an answer, the AI returns:

- result
- what was correct
- missing key points
- misconception warning
- suggested source section
- next review timing

### 5. Concept Map

The map displays:

- concepts as nodes
- relationships as edges
- color by mastery
- filter by collection or time period

Use a simple graph visualization library first. Do not build a custom graph engine.

## Data Model

### profiles

- id
- email
- display_name
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
- created_at

### material_chunks

- id
- user_id
- material_id
- chunk_index
- text
- token_count
- embedding
- created_at

### concepts

- id
- user_id
- collection_id
- material_id
- name
- explanation
- analogy
- source_chunk_ids
- mastery_score
- created_at

### concept_relationships

- id
- user_id
- collection_id
- from_concept_id
- to_concept_id
- relationship_type
- explanation

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
- status
- due_at
- interval_days
- ease
- last_result

### review_attempts

- id
- user_id
- review_item_id
- question_id
- answer
- result
- score
- feedback
- created_at

## AI Workflows

### Extract Concepts

Input:

- material title
- collection name
- chunk text

Output:

- concepts
- analogies
- relationships
- questions
- source references

Use Structured Outputs to keep the response saveable.

### Judge Understanding

Input:

- concept
- expected answer
- rubric
- learner answer
- relevant source chunks

Output:

- score
- pass status
- missing points
- feedback
- suggested review action

### Search Support

Use embeddings for:

- finding related concepts
- retrieving source chunks for judging
- helping the user search their saved knowledge

Plain language: embeddings turn text into numbers so the database can find similar meaning, not just matching words.

## Review Algorithm

Start simple:

- pass: review in 3 days
- strong pass: review in 7 days
- partial: review tomorrow
- fail: review today again

Do not implement a complex spaced repetition algorithm first.

Later:

- tune intervals based on repeated review history
- add mastery score
- add forgetting-risk dashboard

## Implementation Steps

### Step 1: Auth and Collections

- Add Supabase Auth.
- Add protected routes.
- Add collection CRUD.

Validation:

- signed-in user can create a collection
- user cannot see another user's data

### Step 2: Material Input

- Add paste input.
- Add Markdown upload.
- Add PDF text extraction.
- Store files in Supabase Storage.
- Store extracted text in Postgres.

Validation:

- upload a PDF
- view extracted text
- delete or replace failed ingestion manually

### Step 3: Concept Extraction

- Add AI extraction endpoint.
- Store concepts, questions, relationships, and source references.
- Add approval/edit UI.

Validation:

- generate concepts from one real lesson
- edit one concept
- confirm review uses the edited version

### Step 4: Review Queue

- Add `review_items`.
- Add due review page.
- Add flashcard mode.
- Add answer input mode.

Validation:

- failing an answer schedules earlier review
- passing an answer schedules later review

### Step 5: Concept Map

- Render concepts and relationships.
- Filter by collection and time period.
- Color by mastery.

Validation:

- graph loads for 20 concepts
- graph remains readable
- clicking node opens concept detail

### Step 6: Search and Retrieval

- Generate embeddings for chunks and concepts.
- Add semantic search.
- Use retrieved chunks in answer judging.

Validation:

- search for a paraphrase and find the right concept
- judge answer using relevant source chunks

## Plain-Language Tradeoffs

### Pros

- Stronger product than Option A.
- Real file upload support starts early.
- Better answer judging because source chunks can be retrieved.
- Better long-term data model.
- Still avoids the biggest hard problems.

### Cons

- More moving parts.
- PDF parsing can be messy.
- Embeddings add cost and complexity.
- You must design data permissions carefully.

## Main Risk

This version can become too broad if file ingestion expands too quickly.

Mitigation:

- Only support pasted text, Markdown, and PDF in the first real MVP.
- Treat Word, Google Docs, Excel, and image OCR as later importers.
- Keep the review loop as the main product, not file upload.

## Success Criteria

- A learner can create a collection.
- A learner can paste or upload one source.
- The app generates concepts and questions.
- The learner can edit generated concepts.
- The learner can review due concepts.
- The app can point feedback back to a source section.
- The learner can search for a concept using natural wording.

## Recommended First Build

Build this version if you want Recall Map to become a serious portfolio project.

It is more work than Option A, but it gives the product a real foundation without jumping into every possible file type.

## References

- Next.js docs: https://nextjs.org/docs
- Supabase SSR auth docs: https://supabase.com/docs/guides/auth/server-side/creating-a-client?queryGroups=framework&framework=nextjs
- Supabase Storage upload docs: https://supabase.com/docs/guides/storage/uploads/standard-uploads
- Supabase vector columns docs: https://supabase.com/docs/guides/ai/vector-columns
- OpenAI Responses API text generation docs: https://developers.openai.com/api/docs/guides/text
- OpenAI Structured Outputs docs: https://developers.openai.com/api/docs/guides/structured-outputs
