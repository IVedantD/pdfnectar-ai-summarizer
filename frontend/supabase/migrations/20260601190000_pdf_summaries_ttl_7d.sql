-- Auto-delete pdf_summaries older than 7 days.
-- Uses pg_cron to run daily at 03:00 UTC.

-- 1) Deletion function (runs with elevated privileges)
CREATE OR REPLACE FUNCTION public.delete_old_pdf_summaries()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM public.pdf_summaries
  WHERE created_at < (now() - interval '7 days');
END;
$$;

-- 2) Schedule it (best-effort)
DO $$
DECLARE
  existing_job_id int;
BEGIN
  -- Enable pg_cron if available in this project.
  BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
  EXCEPTION
    WHEN insufficient_privilege THEN
      -- Extension creation might be restricted; ignore and continue.
      NULL;
  END;

  -- If pg_cron isn't available, stop here without failing migration.
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    RETURN;
  END IF;

  SELECT jobid INTO existing_job_id
  FROM cron.job
  WHERE jobname = 'delete_old_pdf_summaries_daily';

  IF existing_job_id IS NOT NULL THEN
    PERFORM cron.unschedule(existing_job_id);
  END IF;

  PERFORM cron.schedule(
    'delete_old_pdf_summaries_daily',
    '0 3 * * *',
    $cron$SELECT public.delete_old_pdf_summaries();$cron$
  );
END;
$$;

