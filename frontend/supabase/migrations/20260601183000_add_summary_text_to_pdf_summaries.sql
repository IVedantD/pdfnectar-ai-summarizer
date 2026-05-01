-- Add stored summary text so history items can be opened later.

ALTER TABLE public.pdf_summaries
  ADD COLUMN IF NOT EXISTS document_id UUID,
  ADD COLUMN IF NOT EXISTS summary_text TEXT;

