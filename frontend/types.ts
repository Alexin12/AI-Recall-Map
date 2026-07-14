// Hand-synced with the backend Pydantic model app/main.py -> Ping.
// Keep these fields in step with the backend response shape.
export type Ping = {
  id: string;
  message: string;
  created_at: string;
};

// Hand-synced with the backend Pydantic model app/topics.py -> Topic.
export type Topic = {
  id: string;
  name: string;
  created_at: string;
};
