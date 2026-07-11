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

Review means the learner must retrieve knowledge from memory through flashcards, written explanations, or concept-connection questions, it follow Feynman Technique:
    - Student can select a concept manually --set goal
    - flash card or tten explanations -- teach it to a child 
    - LLM define if the answer good enough to pass--Review and Refine
    - Iterate the above 3 steps to get better understanding--Simplify and organize

 it could be user actively want to review certian concepts or concepts leaned in certain days , but it could also be app planed review.

 Planed review just follow "22. How complex should spaced repetition be first?" for V1.

Finally goal of planed review:
 Planed review means app should set automate review reminder for specific concept by following Forgetting Curve.
 for example, user just learned fast API, then the reminder shecdule will require student go through Feynman Technique process in the following period:
    - 1 hour
    - 9 hours
    - 1 day
    - 2 days
    - 6 days
    - 1 months


### 6. What does "understanding" mean in this app?

Understanding means the learner can 
    - Recognize the concept(flashcard)
    - explain the concept in their own words, include key points, avoid major misconceptions(blank filler questions)
    - connect it to related concepts.

### 7. What does "concept map" mean?


A concept map is a visual graph of concepts and relationships. It is used for navigation and connection, not decoration.

User can jump into specific concept or test of that concept by click object of that concept in the map.

The relationships between different concept object be connected by lines.

### 8. What is the first successful session?


- A learner can add one material
- App can return gets useful concepts and questions
- App can allowed users to answer questions by typeing answer themself
- reviews at least one concept, and sees what to review next.
- Have a basic map, if only have one concept , just show one circle or dot


## Scope

### 9. What should V1 input support?


V1 should support pasted text first. Markdown and PDF can come next. Word, Google Docs, Excel, and images should wait.


### 10. Should PDF be in the first build?


Only include PDF if pasted text and Markdown already work.

### 11. Should Google Docs be in V1?


No. It adds auth, permissions, import edge cases, and privacy concerns.

### 12. Should image OCR be in V1?



No. OCR adds accuracy problems before the review loop is proven.

### 13. Should Excel be in V1?


No. Excel is usually structured data, not normal learning text. It should be a separate later importer.

### 14. Should reminders be email, in-app, or browser notifications?


Start with an in-app due review list. Add email reminders later. Avoid browser notifications in the first build.

### 15. Should users edit AI-generated concepts?


Yes. The user should be able to approve, edit, or delete concepts before relying on them.

### 16. Should every concept become a review item?



No. Important concepts should become review items. Low-value concepts can stay searchable but not due for review.
But we need to discuss more about how we define high or low value concepts.
My thinking for now is, app generate a recommended list of concepts by LLM everytime user upload some materials, 

## Learning System

### 17. What review modes should V1 include?


Start with flashcard and written explanation, use can choose.

### 18. Should AI decide if the learner passes?


Yes, but the decision should be shown as guidance, not absolute truth.
and I am not sure what shows to user , we need to discuss more

### 19. What should AI feedback include?


AI feedback should include result, correct points, missing points, misconception warnings, and suggested next review.

### 20. What should the learner see after failing?



They should see what was missing, a short source-based explanation, and the concept should stay due soon.

### 21. What should the learner see after passing?


They should see brief confirmation, then the concept should move to a later review date.

### 22. How complex should spaced repetition be first?



Use simple rules first: fail means today again, partial means tomorrow, pass means 3 days, strong pass means 7 days.


### 23. Should the app show mastery score?


Yes, but keep it simple: weak, learning, strong. Avoid fake precision like 83 percent mastery in V1.

V2 or V3 we can develop a real score for specific concept, for example "dependency injection in python",
use get 90%, since user correct about 9 questions out of total 10 questions related to concept "dependency injection in python".

## AI Behavior

### 24. Should the AI summarize or extract?


Extract. The app needs structured concepts, questions, relationships, and source references, not only paragraphs.

### 25. Should extraction use Structured Outputs?

Yes. The model should return a schema the app can save.

we can discuss later the elements in Structured Outputs.

### 26. Should the app use RAG in V1?


Not in the first tiny build. Add retrieval after pasted text review works.

### 27. When is RAG actually needed?


RAG is needed when the app must grade answers using the learner's own source material or search across many saved materials.

### 28. Should the app use OpenAI File Search or Supabase pgvector?
OpenAI File Search since user require fast speed for grading


### 29. Should prompts be stored in code or database?

I need more explains to identify the differences

### 30. Should model output be trusted automatically?


No. Save AI confidence and let the user edit generated concepts.

## Data And Domain Model

### 31. What is the difference between material and concept?



Material is the original source. Concept is an idea extracted from the source.

### 32. What is the difference between concept and question?



A concept is what the learner should understand. A question is one way to test that concept.

### 33. What is the difference between collection and material?



A collection groups related learning materials. A material is one source inside that collection.

### 34. What should be the canonical domain terms?


Not fully understand your questions, need you clarify more.

### 35. Should "Mind Map" or "Concept Map" be the canonical term?



Use Concept Map.

### 36. Should a concept belong to one material or many materials?



A concept can be supported by many materials. Start by creating it from one material, then later merge duplicates across materials.

### 37. Should duplicate concepts be allowed?

They may happen during extraction, but the product should eventually merge them.

different materials may include same concept but focus on different points.

for example , material 1 include Fastapi overall high level understanding includes what is fastapi, difference between other api.

material 2 include technical details such as what is path paramaters , why we use it.

final concept should be extract knowledge from 2 materials and then merge them, final concept should includes:
 Fastapi overall high level understanding +technical details.



### 38. Should original material be stored forever?



Store it by default, but give the user a delete option.

### 39. Should the app store learner answers?


Yes. Answers are needed for review history and progress.

### 40. Should the app store AI feedback?

Yes. Store feedback with each review attempt so progress can be inspected later.

## UI And Experience

### 41. What is the first screen after sign-in?


The first screen should be the review dashboard, not a marketing page.
review dashboard should includes at least :
    - Current date.
    - User name.
    - Number of concepts categorized by the level of master by user so far: concept not pass last time show red, strong pass show green, normal pass should blue.For example, 5 red litte squares, 3 blue squares, 6 green squares.(It is a visual board may movivate user to do manual review)
    - high level Review plan in next 5 days : how many red  , blue, green concept should be review in each workday.(auto review reminder)

### 42. What should the dashboard prioritize?


Due review first, then recently learned concepts, then collections.

### 43. Should the app show time tabs like yesterday and last week?



Yes, but they should support review and reflection, not replace the due queue.

### 44. What should a concept card show?


concept card is only used for concept card only, unless you have another usage that i don't know. 
Name, one-line explanation, analogy, mastery state, due state, and source link.

### 45. What happens when the user clicks a concept?

sync user can click a concept in different places, for example, user can click the concept in dashboards, and also can click in flashcard, and can also click in concept map, and when user collect a specific concept, it will Open a concept detail page with explanation, analogy, source, relationships, questions, and review history.

### 46. Should the concept map be on the dashboard?
i think there is no need to show the concept map on the dashboard. my original thought is one big concept the user is learning, for example, fastapi is a very big concept, then it should have their own dashboard and also own concept maps. so dashboard one would be one concept and the user can jump into its corresponding concept map by click a link on dashboard. 

feel free to discuss more with me. 

### 47. What should the app avoid showing?

i'm not quite sure the relationships between app and dashboards and concept maps. i think app is just the overall application, and dashboards was included in the app. concept also includes in the map. everything was included in the app.

tell me if you need more clarification or discussion. 

Avoid long AI summaries, large walls of text, and too many dashboard metrics.

## Technical Architecture

### 48. Should the app be one Next.js app or separate frontend/backend?



Use one Next.js app first for now.

### 49. Should the app use Server Actions or Route Handlers?
not sure the difference. i need to have more discussion and clarification with you. 



### 50. Should background jobs be added immediately?

Tell me the trade offs , not fullt understand.
### 51. Should Supabase Row Level Security be used?


Yes. User learning data must be protected by database-level rules.

### 52. Should the app use a graph database?



No. Store relationships in Postgres first, if Postgres can handle all functions.

### 53. Should the app use AI SDK v6?



Tell me the trade offs , not fullt understand.
### 54. Should embeddings be generated immediately?



Only after core extraction and review work. Embeddings are useful for search and RAG, not required for the first review loop.

### 55. Should uploaded files go into Supabase Storage?


Tell me the trade offs , not fullt understand.

and i also need to know what's the difference between supabase storage and postgresql storage. 

### 56. Should large files be allowed?


Not in V1. Start with small files and clear size limits.

## Privacy And Trust

### 57. What privacy promise should V1 make?



User materials are private to the user and used only to generate their study artifacts.

### 58. Should users be warned about AI mistakes?



Yes, but keep it short. The app should also allow editing incorrect concepts.

### 59. Should user material be used for public examples?



No.

### 60. Should the app support deleting all user data?

Eventually yes. For V1, at least support deleting materials and generated study artifacts.

## MVP Decision

### 61. Which plan should be built first?

not sure.

### 62. What is the first milestone?



Pasted text in, concepts and questions out, review attempt saved.

### 63. What is the second milestone?


Review dashboard can show current user performance on certian big topics.

### 64. What is the third milestone?



- Written-answer grading with specific feedback.
- User can review concepts map for specific big concepts when upload more than 1 unduplicated concepts materials.

### 65. What should be delayed until after real usage?



Complex RAG, all file types, mobile app, collaboration, public sharing, payments, and advanced analytics.

### 66. UI design 
I’d like to discuss the UI design with you. My current idea revolves around "big concepts"—such as FastAPI, RAG, or video editing—which are broad topics. Under each big concept, there would be a set of dashboards; specifically, a dashboard page would be linked to a concept map.

However, this might sound a bit complex. I’m wondering if the user concept assessment phase requires a separate UI—perhaps a new dashboard. Let’s assume, for instance, that we are dealing with a single big concept like FastAPI. Would the first dashboard be the primary one—tracking the user's current understanding of the concept (e.g., identifying which sub-concepts have been mastered versus those that haven't)?

Then, the second dashboard would display the concept map, visualizing the relationships between the sub-concepts—such as path parameters, routers, query parameters, and authentication within FastAPI. Finally, would the third dashboard be used for user assessment—testing their knowledge through methods like flashcards or requiring them to manually input their understanding of a specific concept?

That is roughly how I envision it, but I’d like to discuss it with you—especially regarding technical feasibility.

### plans
Option B' or C are old plans that before I fill Grill_Questions_V1.md
We may need to update or re-write plans
