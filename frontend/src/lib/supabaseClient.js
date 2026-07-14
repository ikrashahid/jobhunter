import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase env vars. Create a .env.local file in frontend/ with " +
    "VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (see .env.local.example)."
  );
}

// IMPORTANT: this must be the Supabase "anon" public key, never the
// service_role key used by the Python backend. The anon key is safe to
// ship in frontend code as long as Row Level Security (RLS) is enabled
// on the matches/postings tables with a read-only policy — see README.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
