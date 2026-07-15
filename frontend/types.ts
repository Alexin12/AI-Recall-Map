// Hand-synced with the backend Pydantic model app/main.py -> Ping.
// Keep these fields in step with the backend response shape.
export type Ping = {
  id: string;
  message: string;
  created_at: string;
};

// Hand-synced with the backend Pydantic model app/goals.py -> Goal.
export type Goal = {
  id: string;
  content: string;
  created_at: string;
  updated_at: string;
};

// Hand-synced with the backend Pydantic model app/topics.py -> Topic.
export type Topic = {
  id: string;
  name: string;
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
  topic_id: string;
  material_id: string;
  name: string;
  explanation: string;
  source_snippet: string;
  goal_relevance: "irrelevant" | "supporting" | "core";
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

// Hand-synced with the backend Pydantic model app/materials.py -> Material.
export type Material = {
  id: string;
  topic_id: string;
  content: string;
  created_at: string;
};
