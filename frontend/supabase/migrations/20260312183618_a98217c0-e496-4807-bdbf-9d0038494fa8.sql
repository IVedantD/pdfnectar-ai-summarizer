
-- Delete existing rows (no user association)
DELETE FROM public.pdf_summaries;

-- Add user_id column
ALTER TABLE public.pdf_summaries ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;

-- Drop old permissive policies
DROP POLICY "Allow public read" ON public.pdf_summaries;
DROP POLICY "Allow public insert" ON public.pdf_summaries;
DROP POLICY "Allow public delete" ON public.pdf_summaries;

-- Create user-scoped policies
CREATE POLICY "Users can view own summaries" ON public.pdf_summaries
  FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own summaries" ON public.pdf_summaries
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own summaries" ON public.pdf_summaries
  FOR DELETE TO authenticated USING (auth.uid() = user_id);
