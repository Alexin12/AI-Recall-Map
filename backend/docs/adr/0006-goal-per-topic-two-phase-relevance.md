# Goal is an attribute of a Topic, relevance scored in a second phase

Goal moves from one global per-user objective to a nullable `goal` column on each Topic; the user-level `goals` table is dropped and existing global-goal data is abandoned (no migration). A real learner runs several parallel subjects — a student with maths, programming, accounting — that should not be judged against one blended objective. A Topic with no Goal simply has no review plan: its Concepts stay browsable on the Concept Map, but their `goal_relevance` is left null and nothing is scheduled.

Because relevance can only be judged once the Topic's Goal is known — and a newly created Topic gets its Goal from the user on the confirmation screen — extraction splits into two phases. Phase 1 (always) extracts and routes Concepts. Phase 2 (only for Topics that have a Goal) scores each Concept's relevance and builds its review schedule. Scoring runs **after** the user sets goals and is **auto-applied** — there is no pre-commit review screen. The user overrides the result later on the Topic page, via a per-Concept relevance column they can toggle. Relevance stays three-state: irrelevant / supporting / core.

**Status**: accepted

**Consequences**:
- Goal is no longer a domain entity with its own page — it is documented as an attribute of a Topic.
- The M1 "core pre-checked, user toggles on the confirmation screen" control moves to the Topic page; the AI-as-guidance / one-click-override promise is preserved, just relocated to after commit.
- The confirmation screen is slimmed to Topic routing + optional Goal-setting; per-Concept scheduling toggles are removed from it.
