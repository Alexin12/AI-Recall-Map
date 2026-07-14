import { createClient } from "@supabase/supabase-js";

// Browser client: the anon key is public and works together with RLS.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);
