# Recall Map Grill Questions v1

## How To Use This File

Answer these questions before implementation.

Each question includes a recommended answer. If you agree, write "agree". If not, write your own answer.

The goal is to remove fuzzy product and technical decisions before coding.

## Product Definition

### 1. Who is the first user?


The first user is a self-directed learner taking online courses, reading articles, or studying transcripts, who maybe or may not already uses AI while learning but forgets the material later.


### 2. What is the main pain?

The main pain is not "I need summaries." The main pain is "I learned something, but I do not have a reliable way to recall, test, and reconnect it later."

### 3. What promise should Recall Map make?

Recall Map turns learning material into active recall questions, concept explanations, and concept relationships, then brings them back when review is due.

### 4. What should the product not become?


It should not become a general notes app, a chatbot over documents, or a file storage app.

### 5. What does "review" mean in this app?

Review means the learner must retrieve knowledge from memory through flashcards, written explanations, or concept-connection questions, it could be user actively want to review certian concepts or concepts leaned in certain days , but it could also be app planed review.

### 6. What does "understanding" mean in this app?

Understanding means the learner can 
    - Recognize the concept(flashcard)
    - explain the concept in their own words, include key points, avoid major misconceptions(blank filler questions)
    - connect it to related concepts.

### 7. What does "concept map" mean?


A concept map is a visual graph of concepts and relationships. It is used for navigation and connection, not decoration.
### 8. What is the first successful session?


- A learner can add one material
- App can return gets useful concepts and questions
- App can allowed users to answer questions by typeing answer themself
- reviews at least one concept, and sees what to review next.

--------------------------------------------------------------------------------------------------------------------------------------

## Scope

### 9. What should V1 input support?

Recommended answer:

V1 should support pasted text first. Markdown and PDF can come next. Word, Google Docs, Excel, and images should wait.

Plain-language tradeoff:

Pasted text is boring but reliable. File parsing looks impressive but can consume the whole project.

### 10. Should PDF be in the first build?

Recommended answer:

Only include PDF if pasted text and Markdown already work.

### 11. Should Google Docs be in V1?

Recommended answer:

No. It adds auth, permissions, import edge cases, and privacy concerns.

### 12. Should image OCR be in V1?

Recommended answer:

No. OCR adds accuracy problems before the review loop is proven.

### 13. Should Excel be in V1?

Recommended answer:

No. Excel is usually structured data, not normal learning text. It should be a separate later importer.

### 14. Should reminders be email, in-app, or browser notifications?

Recommended answer:

Start with an in-app due review list. Add email reminders later. Avoid browser notifications in the first build.

### 15. Should users edit AI-generated concepts?

Recommended answer:

Yes. The user should be able to approve, edit, or delete concepts before relying on them.

### 16. Should every concept become a review item?

Recommended answer:

No. Important concepts should become review items. Low-value concepts can stay searchable but not due for review.

## Learning System

### 17. What review modes should V1 include?

Recommended answer:

Start with flashcard and written explanation. Add compare-two-concepts later.

### 18. Should AI decide if the learner passes?

Recommended answer:

Yes, but the decision should be shown as guidance, not absolute truth.

### 19. What should AI feedback include?

Recommended answer:

AI feedback should include result, correct points, missing points, misconception warnings, and suggested next review.

### 20. What should the learner see after failing?

Recommended answer:

They should see what was missing, a short source-based explanation, and the concept should stay due soon.

### 21. What should the learner see after passing?

Recommended answer:

They should see brief confirmation, then the concept should move to a later review date.

### 22. How complex should spaced repetition be first?

Recommended answer:

Use simple rules first: fail means today again, partial means tomorrow, pass means 3 days, strong pass means 7 days.

Plain-language tradeoff:

A simple schedule is easy to understand and debug. A complex algorithm can wait until real usage exists.

### 23. Should the app show mastery score?

Recommended answer:

Yes, but keep it simple: weak, learning, strong. Avoid fake precision like 83 percent mastery in V1.

## AI Behavior

### 24. Should the AI summarize or extract?

Recommended answer:

Extract. The app needs structured concepts, questions, relationships, and source references, not only paragraphs.

### 25. Should extraction use Structured Outputs?

Recommended answer:

Yes. The model should return a schema the app can save.

Plain-language tradeoff:

Structured Outputs are like asking the AI to fill a form. Normal text is like asking it to write an essay.

### 26. Should the app use RAG in V1?

Recommended answer:

Not in the first tiny build. Add retrieval after pasted text review works.

### 27. When is RAG actually needed?

Recommended answer:

RAG is needed when the app must grade answers using the learner's own source material or search across many saved materials.

### 28. Should the app use OpenAI File Search or Supabase pgvector?

Recommended answer:

Use Supabase pgvector if you want control and product-specific search. Use OpenAI File Search if speed matters more than control.

Plain-language tradeoff:

Supabase pgvector is like owning the library catalog. OpenAI File Search is like asking another service to manage the catalog for you.

### 29. Should prompts be stored in code or database?

Recommended answer:

Store prompt templates in code at first. Move them to database only when non-developers need to edit them.

### 30. Should model output be trusted automatically?

Recommended answer:

No. Save AI confidence and let the user edit generated concepts.

## Data And Domain Model

### 31. What is the difference between material and concept?

Recommended answer:

Material is the original source. Concept is an idea extracted from the source.

### 32. What is the difference between concept and question?

Recommended answer:

A concept is what the learner should understand. A question is one way to test that concept.

### 33. What is the difference between collection and material?

Recommended answer:

A collection groups related learning materials. A material is one source inside that collection.

### 34. What should be the canonical domain terms?

Recommended answer:

Use Workspace, Collection, Material, Chunk, Concept, Relationship, Question, Review Item, and Review Attempt.

### 35. Should "Mind Map" or "Concept Map" be the canonical term?

Recommended answer:

Use Concept Map.

Reason:

The product focuses on relationships between knowledge concepts, not only a tree-shaped brainstorming map.

### 36. Should a concept belong to one material or many materials?

Recommended answer:

A concept can be supported by many materials. Start by creating it from one material, then later merge duplicates across materials.

### 37. Should duplicate concepts be allowed?

Recommended answer:

They may happen during extraction, but the product should eventually merge them.

### 38. Should original material be stored forever?

Recommended answer:

Store it by default, but give the user a delete option.

### 39. Should the app store learner answers?

Recommended answer:

Yes. Answers are needed for review history and progress.

### 40. Should the app store AI feedback?

Recommended answer:

Yes. Store feedback with each review attempt so progress can be inspected later.

## UI And Experience

### 41. What is the first screen after sign-in?

Recommended answer:

The first screen should be the review dashboard, not a marketing page.

### 42. What should the dashboard prioritize?

Recommended answer:

Due review first, then recently learned concepts, then collections.

### 43. Should the app show time tabs like yesterday and last week?

Recommended answer:

Yes, but they should support review and reflection, not replace the due queue.

### 44. What should a concept card show?

Recommended answer:

Name, one-line explanation, analogy, mastery state, due state, and source link.

### 45. What happens when the user clicks a concept?

Recommended answer:

Open a concept detail page with explanation, analogy, source, relationships, questions, and review history.

### 46. Should the concept map be on the dashboard?

Recommended answer:

Show a small preview on the dashboard and a full map on its own page.

### 47. What should the app avoid showing?

Recommended answer:

Avoid long AI summaries, large walls of text, and too many dashboard metrics.

## Technical Architecture

### 48. Should the app be one Next.js app or separate frontend/backend?

Recommended answer:

Use one Next.js app first.

Plain-language tradeoff:

One app is easier to build and deploy. Separate services are useful later when background work becomes heavy.

### 49. Should the app use Server Actions or Route Handlers?

Recommended answer:

Use Server Actions for normal form mutations and Route Handlers for AI or file-processing endpoints.

### 50. Should background jobs be added immediately?

Recommended answer:

No. Add them when file ingestion or AI extraction becomes slow enough to block the user.

### 51. Should Supabase Row Level Security be used?

Recommended answer:

Yes. User learning data must be protected by database-level rules.

### 52. Should the app use a graph database?

Recommended answer:

No. Store relationships in Postgres first.

Plain-language tradeoff:

A graph database sounds natural, but Postgres is simpler and good enough for early concept relationships.

### 53. Should the app use AI SDK v6?

Recommended answer:

Optional. Use it if you want provider flexibility and UI helpers. Use OpenAI SDK directly if you want fewer layers.

### 54. Should embeddings be generated immediately?

Recommended answer:

Only after core extraction and review work. Embeddings are useful for search and RAG, not required for the first review loop.

### 55. Should uploaded files go into Supabase Storage?

Recommended answer:

Yes, if file upload exists. Store metadata and extracted text in Postgres.

### 56. Should large files be allowed?

Recommended answer:

Not in V1. Start with small files and clear size limits.

## Privacy And Trust

### 57. What privacy promise should V1 make?

Recommended answer:

User materials are private to the user and used only to generate their study artifacts.

### 58. Should users be warned about AI mistakes?

Recommended answer:

Yes, but keep it short. The app should also allow editing incorrect concepts.

### 59. Should user material be used for public examples?

Recommended answer:

No.

### 60. Should the app support deleting all user data?

Recommended answer:

Eventually yes. For V1, at least support deleting materials and generated study artifacts.

## MVP Decision

### 61. Which plan should be built first?

Recommended answer:

Build Option A if speed matters most. Build Option B if this is a serious portfolio product. Do not start with Option C unless the goal is specifically to learn RAG.

### 62. What is the first milestone?

Recommended answer:

Pasted text in, concepts and questions out, review attempt saved.

### 63. What is the second milestone?

Recommended answer:

Review dashboard with due concepts and time filters.

### 64. What is the third milestone?

Recommended answer:

Written-answer grading with specific feedback.

### 65. What should be delayed until after real usage?

Recommended answer:

Complex RAG, all file types, mobile app, collaboration, public sharing, payments, and advanced analytics.

## Final Recommendation

Start with Option A's build order and Option B's data model.

Reason:

Option A keeps the first implementation simple, while Option B's naming and tables prevent a rewrite when the app grows.
