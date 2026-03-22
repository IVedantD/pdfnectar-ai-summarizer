
-- Create table for PDF summary history
CREATE TABLE public.pdf_summaries (
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
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.pdf_summaries ENABLE ROW LEVEL SECURITY;

-- For now, allow public read/write (no auth yet)
CREATE POLICY "Allow public read" ON public.pdf_summaries FOR SELECT USING (true);
CREATE POLICY "Allow public insert" ON public.pdf_summaries FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public delete" ON public.pdf_summaries FOR DELETE USING (true);
