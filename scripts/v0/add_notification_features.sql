-- Add to challenges table
ALTER TABLE public.challenges ADD COLUMN IF NOT EXISTS scheduler_job_ids JSONB;
ALTER TABLE public.challenges ADD COLUMN IF NOT EXISTS checkin_time TIMESTAMPTZ;

-- Add users FCM token storage
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS fcm_token TEXT; 