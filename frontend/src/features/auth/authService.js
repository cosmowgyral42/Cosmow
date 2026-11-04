import { supabase } from "../../lib/supabase.js";

function getClient() {
  if (!supabase) {
    throw new Error("Supabase is not configured. Check your frontend environment settings.");
  }
  return supabase;
}

export async function signUp(email, password) {
  const client = getClient();
  const { data, error } = await client.auth.signUp({
    email: email.trim().toLowerCase(),
    password,
    options: {
      emailRedirectTo: `${window.location.origin}/login`,
    },
  });

  if (error) throw error;
  return data;
}

export async function signIn(email, password) {
  const { data, error } = await getClient().auth.signInWithPassword({
    email: email.trim().toLowerCase(),
    password,
  });

  if (error) throw error;
  return data;
}

export async function signOut() {
  const { error } = await getClient().auth.signOut();
  if (error) throw error;
}