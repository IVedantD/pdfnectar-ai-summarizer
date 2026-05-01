-- History: pdf_summaries + RLS (idempotent). Fixes "Could not find the table public.pdf_summaries in the schema cache".

CREATE TABLE IF NOT EXISTS public.pdf_summaries (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    summary_length TEXT NOT NULL DEFAULT 'medium',
    language TEXT NOT NULL DEFAULT 'en',
    key_points JSONB,
    tables_formulas TEXT,
    action_items JSONB,
    word_count INTEGER,
    reading_time TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add user_id if an older migration created the table without it
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'pdf_summaries'
      AND column_name = 'user_id'
  ) THEN
    DELETE FROM public.pdf_summaries;
    ALTER TABLE public.pdf_summaries
      ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END $$;

ALTER TABLE public.pdf_summaries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read" ON public.pdf_summaries;
DROP POLICY IF EXISTS "Allow public insert" ON public.pdf_summaries;
DROP POLICY IF EXISTS "Allow public delete" ON public.pdf_summaries;
DROP POLICY IF EXISTS "Users can view own summaries" ON public.pdf_summaries;
DROP POLICY IF EXISTS "Users can insert own summaries" ON public.pdf_summaries;
DROP POLICY IF EXISTS "Users can delete own summaries" ON public.pdf_summaries;

CREATE POLICY "Users can view own summaries" ON public.pdf_summaries
  FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own summaries" ON public.pdf_summaries
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own summaries" ON public.pdf_summaries
  FOR DELETE TO authenticated USING (auth.uid() = user_id);

GRANT SELECT, INSERT, DELETE ON public.pdf_summaries TO authenticated;
GRANT ALL ON public.pdf_summaries TO service_role;
