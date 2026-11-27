BEGIN;

ALTER TABLE public.hospitals
    ADD COLUMN IF NOT EXISTS ward_setup_skipped boolean NOT NULL DEFAULT false;

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'hms_runtime') THEN
        GRANT UPDATE (ward_setup_skipped) ON public.hospitals TO hms_runtime;
    END IF;
END;
$$;

COMMIT;
