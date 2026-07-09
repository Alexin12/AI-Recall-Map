# Recall Map Plan v2 - Option A: Simple Review MVP

## Positioning

Build the smallest useful web app for one learning loop:

1. The learner pastes lesson material.
2. The app extracts key concepts, analogies, relationships, and active recall questions.
3. The learner reviews concepts by day, week, or month.
4. The learner answers short questions.
5. The app records whether the concept needs review.

This version does not try to support every file type first. It proves the core habit: "I learned this, I came back later, and I could test myself."

## Best Fit

Choose this version if the goal is to build something working quickly and avoid getting stuck in ingestion, RAG, file parsing, or complex graph logic.

## Core Scope

### In Scope

- Account sign-in.
- Paste text input.
- Optional Markdown upload only.
- Generate:
  - concepts
  - short explanations
  - analogies
  - active recall questions
  - concept relationships
- Review tabs:
  - Today
  - Yesterday
  - Last 7 days
  - Last 30 days
- Flashcard review.
- Understanding input review.
- Simple AI judgment:
  - pass
  - partial
  - fail
  - missing points
  - suggested review concepts
- Simple concept map using stored relationships.
- Email reminder or in-app reminder list.

### Out of Scope

- PDF, Word, Google Docs, Excel, image, and PNG ingestion.
- RAG over uploaded files.
- Real spaced repetition algorithm.
- Mobile app.
- Collaboration.
- Public sharing.
- Payments.

## Recommended Stack

- Frontend and backend: Next.js 16 App Router.
- Language: TypeScript.
- UI: Tailwind CSS and shadcn/ui.
- Database and auth: Supabase.
- AI calls: OpenAI Responses API.
- Structured extraction: OpenAI Structured Outputs.
- Background jobs: Vercel Cron or Supabase scheduled jobs later.
- Deployment: Vercel.

Plain language: this stack keeps the app in one codebase. Next.js handles pages and server actions, Supabase stores users and learning data, and OpenAI turns messy notes into structured study objects.

## Current API Notes

Checked on 2026-07-08:

- Next.js docs show the latest version as 16.2.10 and recommend App Router for newer React features.
- Supabase recommends `@supabase/ssr` for server-side auth in Next.js and says server code should protect data with verified claims, not only cookie sessions.
- OpenAI docs recommend the Responses API for new text generation apps.
- OpenAI Structured Outputs should be used when the app needs JSON that follows a schema.
- AI SDK v6 exists, but this option can call the OpenAI SDK directly to reduce moving parts.

## Product Flow

### 1. Add Material

User inputs:

- title
- source type
- text content
- optional course name
- optional tags

System action:

- save the original material
- call AI extraction
- save concepts, questions, and relationships

### 2. Review Timeline

The dashboard groups learned material by time:

- Today
- Yesterday
- Last 7 days
- Last 30 days

Each tab shows:

- learned concepts
- one-line explanation
- analogy
- linked concepts
- review status

### 3. Test Understanding

Two modes:

- Flashcard: user marks "I know it" or "Review again".
- Understanding input: user writes their explanation.

The AI judge compares the answer against the stored concept explanation and expected key points.

### 4. Review Suggestions

The app returns plain feedback:

- what the learner understood
- what was missing
- which concepts to review next
- link back to the original material

## Data Model

### users

- id
- email
- created_at

### materials

- id
- user_id
- title
- source_type
- raw_text
- created_at

### concepts

- id
- user_id
- material_id
- name
- explanation
- analogy
- importance
- created_at

### concept_relationships

- id
- user_id
- from_concept_id
- to_concept_id
- relationship_type
- explanation

### questions

- id
- user_id
- concept_id
- question_text
- expected_answer
- difficulty

### review_attempts

- id
- user_id
- concept_id
- question_id
- mode
- user_answer
- result
- missing_points
- created_at

### review_items

- id
- user_id
- concept_id
- status
- next_review_at
- last_reviewed_at

## AI Schema

Use Structured Outputs so the model must return a predictable object:

```json
{
  "concepts": [
    {
      "name": "string",
      "explanation": "string",
      "analogy": "string",
      "importance": "low | medium | high",
      "questions": [
        {
          "question": "string",
          "expected_answer": "string",
          "difficulty": "easy | medium | hard"
        }
      ]
    }
  ],
  "relationships": [
    {
      "from": "string",
      "to": "string",
      "relationship_type": "depends_on | contrasts_with | example_of | related_to",
      "explanation": "string"
    }
  ]
}
```

Plain language: the AI is not allowed to just write a nice paragraph. It must return data that the app can save and display.

## Implementation Steps

### Step 1: Project Shell

- Create Next.js app.
- Add TypeScript, Tailwind CSS, shadcn/ui.
- Add Supabase client helpers.
- Add sign-in and protected dashboard route.

Validation:

- user can sign in
- protected page rejects signed-out users

### Step 2: Material Input

- Add material form.
- Save pasted text to Supabase.
- Show saved material in dashboard.

Validation:

- submit text
- refresh page
- material still appears

### Step 3: AI Extraction

- Add server action or route handler for extraction.
- Use OpenAI Responses API with Structured Outputs.
- Save concepts, questions, and relationships.

Validation:

- paste one lesson
- inspect database rows
- verify the UI shows generated concepts

### Step 4: Review UI

- Add timeline tabs.
- Add concept cards.
- Add simple concept map.

Validation:

- concepts appear under the correct time tab
- empty states are clear

### Step 5: Understanding Test

- Add flashcard review.
- Add text-answer review.
- Add AI judge response.
- Save review attempts.

Validation:

- answer one question well
- answer one question poorly
- verify different feedback

### Step 6: Reminder MVP

- Add `next_review_at`.
- Show "Due today" list.
- Optional: add email reminder later.

Validation:

- reviewed concepts move out of due list
- failed concepts stay due sooner

## Plain-Language Tradeoffs

### Pros

- Fastest version to build.
- Low technical risk.
- Easy to debug because all input starts as text.
- Proves whether learners actually want the review loop.
- Good for a one-month serious project.

### Cons

- Upload support is weak.
- The concept map will be simple.
- AI judgment may feel rough until prompts improve.
- No real retrieval from original documents.

## Main Risk

The app may become "AI summary plus flashcards" if the review loop is not strong enough.

Mitigation:

- Make the dashboard focus on due review, not saved notes.
- Make every concept testable.
- Save review attempts and show progress over time.

## Success Criteria

- A learner can add one lesson in under two minutes.
- The app generates at least five useful review questions.
- The learner can return tomorrow and see what needs review.
- The learner can answer in their own words and get specific feedback.
- The app feels useful before PDF or file upload exists.

## Recommended First Build

Build this version first unless the main goal is to learn file ingestion or RAG.

This version is the cleanest proof of Recall Map's real value: turning learned material into a repeatable recall habit.

## References

- Next.js docs: https://nextjs.org/docs
- Supabase SSR auth docs: https://supabase.com/docs/guides/auth/server-side/creating-a-client?queryGroups=framework&framework=nextjs
- OpenAI Responses API text generation docs: https://developers.openai.com/api/docs/guides/text
- OpenAI Structured Outputs docs: https://developers.openai.com/api/docs/guides/structured-outputs
