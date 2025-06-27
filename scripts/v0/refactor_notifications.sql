-- Step 1: Remove the now-redundant scheduler_job_ids column from the challenges table
ALTER TABLE public.challenges DROP COLUMN IF EXISTS scheduler_job_ids;

-- Step 2: Change the checkin_time column to be TIME instead of TIMESTAMPTZ
-- This stores only the local time of day (e.g., '09:00:00')
ALTER TABLE public.challenges ALTER COLUMN checkin_time TYPE TIME;

-- Step 3: Add a timezone column to the users table to store each user's preference
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS timezone VARCHAR(255) DEFAULT 'UTC';

-- Step 4: Create a new table to track scheduler jobs on a per-participant basis
CREATE TABLE IF NOT EXISTS public.participant_jobs (
    challenge_id UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    scheduler_job_ids JSONB,
    PRIMARY KEY (challenge_id, user_id)
);

-- Step 5: Create an index for faster lookups on the new table
CREATE INDEX IF NOT EXISTS idx_participant_jobs_user_id ON public.participant_jobs(user_id); 