// Hand-synced with the backend Pydantic model app/main.py -> Ping.
// Keep these fields in step with the backend response shape.
export type Ping = {
  id: string;
  message: string;
  created_at: string;
};

// Hand-synced with the backend Pydantic model app/topics.py -> Topic.
// goal is optional per Topic (ADR-0006); null = browse only, never due.
export type Topic = {
  id: string;
  name: string;
  goal: string | null;
  created_at: string;
};

// Hand-synced with the backend Pydantic model app/extraction.py -> Question.
export type Question = {
  id: string;
  concept_id: string;
  kind: "flashcard" | "written";
  prompt: string;
};

// Hand-synced with the backend Pydantic model app/extraction.py -> Concept.
export type Concept = {
  id: string;
  topic_id: string | null;
  material_id: string;
  name: string;
  explanation: string;
  source_snippet: string;
  goal_relevance: "irrelevant" | "supporting" | "core" | null;
  confidence: number;
  scheduled: boolean;
  confirmed: boolean;
  created_at: string;
  questions: Question[];
};

// Hand-synced with the backend Pydantic model app/reviews.py -> Feedback.
export type Feedback = {
  correct_points: string[];
  missing_points: string[];
  misconceptions: string[];
};

// Hand-synced with the backend Pydantic model app/reviews.py -> Review.
export type Review = {
  id: string;
  concept_id: string;
  question_id: string;
  answer: string;
  verdict: "fail" | "partial" | "pass" | "strong";
  ai_verdict: "fail" | "partial" | "pass" | "strong";
  verdict_overridden: boolean;
  feedback: Feedback;
  next_due_at: string;
  created_at: string;
};

// Hand-synced with the backend Pydantic model app/concepts.py -> ConceptDetail.
export type ConceptDetail = Concept & {
  mastery: "never-reviewed" | "weak" | "learning" | "strong";
  due: boolean;
  next_due_at: string;
  reviews: Review[];
};

// Hand-synced with the backend Pydantic models app/concept_map.py (ADR-0007).
export type TreeNode = {
  id: string;
  name: string;
  display_label: string;
  goal_relevance: "irrelevant" | "supporting" | "core" | null;
  scheduled: boolean;
  confirmed: boolean;
  mastery: "never-reviewed" | "weak" | "learning" | "strong";
  children: TreeNode[];
};

export type ConceptMap = {
  tree: TreeNode[];
};

// Hand-synced with the backend Pydantic model app/materials.py -> Material.
export type Material = {
  id: string;
  topic_id: string | null;
  content: string;
  created_at: string;
  concept_names: string[];
};

// Hand-synced with the backend Pydantic models app/home.py.
export type DueDay = {
  date: string;
  count: number;
};

// counts keys are the four Mastery States (never-reviewed/weak/learning/strong);
// consumed by the Memory Forest slice, not rendered on Global Home yet.
export type TopicMasteryCounts = {
  topic_id: string;
  topic_name: string;
  counts: Record<string, number>;
};

export type HomeSummary = {
  review_due_count: number;
  next_five_days: DueDay[];
  recently_learned: Concept[];
  topic_mastery: TopicMasteryCounts[];
  inbox_count: number;
};
