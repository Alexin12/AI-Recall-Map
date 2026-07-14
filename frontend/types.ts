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

// Hand-synced with the backend Pydantic model app/materials.py -> Material.
export type Material = {
  id: string;
  topic_id: string;
  content: string;
  created_at: string;
};
