//provides a singleton Supabase client initialized from backend config to avoid multiple instances across the app

import { createClient, SupabaseClient } from '@supabase/supabase-js';

let supabase: SupabaseClient | null = null;
export async function getSupabaseClient(): Promise<SupabaseClient> {
  if (supabase) return supabase;
  const res = await fetch('http://localhost:8000/config/supabase');
  const config = await res.json();
  supabase = createClient(config.url, config.anon_key);
  return supabase;
}

//for testing other stuff
// const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL!;
// const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY!;
// export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);