# Recall Map is an active-recall gym, not a knowledge organizer

The product's job is to make the human do the cognitive work — retrieve, explain, and reconnect what they learned — not to do that work for them. The feared "competitor" (a folder-scanning agent that reads your notes and hands back a synthesized mind map, Karpathy-style, or a Codex cron that auto-summarizes) solves the *opposite* problem: it thinks *for* the user, which is the very habit this product exists to counter in an age where any answer is five seconds away from an LLM.

Consequently the moat is **behavioral design, not model capability**. Spaced-repetition tools (Anki) are technically trivial and have survived two decades of better AI, because their value was never "the computer can't do this" — it is "the human must do this, on a schedule, with friction by design." Recall Map does not try to win on "our AI organizes better."

**Status**: accepted

**Consequences**:
- The main course is the retrieval loop (flashcard test-before-reveal, Feynman written explanation graded by AI). Auto-classification and routing are back-office plumbing that must stay out of the user's way — never the headline feature.
- The design razor for every feature: **automate the boring (transcription, dedup, filing); make the user do the cognitive act (recalling, explaining, judging).** A feature that does the recalling *for* the user is off-mission even if it demos well.
- The Concept Map is positioned as a reference/navigation shelf and a progress view, not as the recall exercise itself — so auto-generating it does not violate the razor (the recall happens in the review modes).
- Competitive risk is retention/habit (will anyone keep coming back?), the same risk Anki always had — not "an LLM will out-organize us." Effort should flow to the habit loop, not the auto-organizer.
