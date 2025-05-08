-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert sample users
INSERT INTO public.users (id, username, full_name, bio, avatar_url, updated_at) VALUES
    (uuid_generate_v4(), 'alice', 'Alice Sample', 'Loves challenges', 'avatars/alice.jpg', NOW()),
    (uuid_generate_v4(), 'bob', 'Bob Example', 'Ready to build habits', 'avatars/bob.jpg', NOW()),
    (uuid_generate_v4(), 'carol', 'Carol Tester', 'Music enthusiast', 'avatars/carol.jpg', NOW()),
    (uuid_generate_v4(), 'dave', 'Dave Fake', 'Always testing', 'avatars/dave.jpg', NOW()),
    (uuid_generate_v4(), 'eve', 'Eve Test', 'Test user', 'avatars/eve.jpg', NOW()),
    (uuid_generate_v4(), 'frank', 'Frank Doe', 'Placeholder account', 'avatars/frank.jpg', NOW()),
    (uuid_generate_v4(), 'grace', 'Grace Sample', 'Challenge lover', 'avatars/grace.jpg', NOW()),
    (uuid_generate_v4(), 'hank', 'Hank Example', 'Example bio', 'avatars/hank.jpg', NOW()),
    (uuid_generate_v4(), 'iris', 'Iris Tester', 'QA enthusiast', 'avatars/iris.jpg', NOW()),
    (uuid_generate_v4(), 'jack', 'Jack Doe', 'Sample data', 'avatars/jack.jpg', NOW());

-- Insert sample challenges
INSERT INTO public.challenges (id, creator_id, title, description, due_date, location, restriction, repetition, repetition_frequency, repetition_days, check_in_time, created_at, updated_at, is_private, time_window) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'alice'), 'Morning Run', 'Run 1 mile every morning', NOW() + INTERVAL '7 days', 'Central Park', '', 'daily', 1, NULL, '07:00:00', NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days', FALSE, 3600),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'bob'), 'Read a Book', 'Read 30 pages daily', NOW() + INTERVAL '14 days', '', '', 'daily', 1, NULL, '20:00:00', NOW() - INTERVAL '14 days', NOW() - INTERVAL '14 days', FALSE, 86400),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'carol'), 'Yoga Stretch', 'Daily 15-minute yoga stretch', NOW() + INTERVAL '21 days', 'Home', '', 'daily', 1, NULL, '06:30:00', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days', FALSE, 1800),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'dave'), 'Push-Up Challenge', 'Do 50 push-ups', NOW() + INTERVAL '10 days', '', '', 'daily', NULL, NULL, NULL, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', FALSE, NULL);

-- Insert challenge participants
INSERT INTO public.challenge_participants (challenge_id, user_id, joined_at, status) VALUES
    ((SELECT id FROM public.challenges WHERE title = 'Morning Run'), (SELECT id FROM public.users WHERE username = 'alice'), NOW() - INTERVAL '10 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Morning Run'), (SELECT id FROM public.users WHERE username = 'bob'), NOW() - INTERVAL '8 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Morning Run'), (SELECT id FROM public.users WHERE username = 'grace'), NOW() - INTERVAL '7 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Read a Book'), (SELECT id FROM public.users WHERE username = 'carol'), NOW() - INTERVAL '12 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Read a Book'), (SELECT id FROM public.users WHERE username = 'eve'), NOW() - INTERVAL '3 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Yoga Stretch'), (SELECT id FROM public.users WHERE username = 'frank'), NOW() - INTERVAL '4 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Yoga Stretch'), (SELECT id FROM public.users WHERE username = 'iris'), NOW() - INTERVAL '2 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Push-Up Challenge'), (SELECT id FROM public.users WHERE username = 'dave'), NOW() - INTERVAL '2 days', 'active'),
    ((SELECT id FROM public.challenges WHERE title = 'Push-Up Challenge'), (SELECT id FROM public.users WHERE username = 'hank'), NOW() - INTERVAL '1 day', 'active');

-- Insert challenge achievements
INSERT INTO public.challenge_achievements (id, challenge_id, user_id, achievement_type, description, achieved_at, success_count) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Morning Run'), (SELECT id FROM public.users WHERE username = 'alice'), 'success_rate', 'Completed 6 out of 7 runs', NOW() - INTERVAL '1 day', 6),
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Read a Book'), (SELECT id FROM public.users WHERE username = 'carol'), 'success_rate', 'Read 210 pages', NOW() - INTERVAL '2 days', 7),
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Yoga Stretch'), (SELECT id FROM public.users WHERE username = 'iris'), 'success_rate', '15 stretches every day', NOW() - INTERVAL '1 day', 1);

-- Insert posts
INSERT INTO public.posts (id, user_id, content, media_urls, location, is_private, created_at, updated_at, edited, challenge_id) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'alice'), 'Just finished my morning run!', ARRAY['post_media/alice_run1.jpg'], 'Central Park', FALSE, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', FALSE, (SELECT id FROM public.challenges WHERE title = 'Morning Run')),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'bob'), 'Starting my reading challenge tonight.', ARRAY[]::TEXT[], '', FALSE, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', FALSE, (SELECT id FROM public.challenges WHERE title = 'Read a Book')),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'carol'), 'Morning yoga done!', ARRAY['post_media/carol_yoga.jpg'], 'Home', FALSE, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day', FALSE, (SELECT id FROM public.challenges WHERE title = 'Yoga Stretch')),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'dave'), 'Pushed out 50 push-ups!', ARRAY['post_media/dave_pushup.jpg'], '', FALSE, NOW() - INTERVAL '12 hours', NOW() - INTERVAL '12 hours', FALSE, (SELECT id FROM public.challenges WHERE title = 'Push-Up Challenge'));

-- Insert comments
INSERT INTO public.comments (id, post_id, user_id, content, parent_comment_id, created_at) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.posts WHERE content LIKE 'Just finished%'), (SELECT id FROM public.users WHERE username = 'bob'), 'Great job, Alice!', NULL, NOW() - INTERVAL '23 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.posts WHERE content LIKE 'Starting my reading%'), (SELECT id FROM public.users WHERE username = 'eve'), 'Good luck, Bob!', NULL, NOW() - INTERVAL '20 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.posts WHERE content LIKE 'Morning yoga done%'), (SELECT id FROM public.users WHERE username = 'frank'), 'Impressive flexibility!', NULL, NOW() - INTERVAL '18 hours');

-- Insert likes
INSERT INTO public.likes (id, user_id, post_id, comment_id, created_at) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'grace'), (SELECT id FROM public.posts WHERE content LIKE 'Just finished%'), NULL, NOW() - INTERVAL '22 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'hank'), NULL, (SELECT id FROM public.comments WHERE content LIKE 'Great job%'), NOW() - INTERVAL '21 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'iris'), (SELECT id FROM public.posts WHERE content LIKE 'Pushed out%'), NULL, NOW() - INTERVAL '10 hours');

-- Insert follows
INSERT INTO public.follows (id, follower_id, followed_id, created_at) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'bob'), (SELECT id FROM public.users WHERE username = 'alice'), NOW() - INTERVAL '3 days'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'carol'), (SELECT id FROM public.users WHERE username = 'alice'), NOW() - INTERVAL '2 days'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'eve'), (SELECT id FROM public.users WHERE username = 'bob'), NOW() - INTERVAL '1 day');

-- Insert hashtags
INSERT INTO public.hashtags (id, name, usage_count, created_at) VALUES
    (uuid_generate_v4(), 'running', 12, NOW() - INTERVAL '7 days'),
    (uuid_generate_v4(), 'reading', 8, NOW() - INTERVAL '14 days'),
    (uuid_generate_v4(), 'yoga', 5, NOW() - INTERVAL '5 days'),
    (uuid_generate_v4(), 'pushup', 3, NOW() - INTERVAL '2 days');

-- Insert challenge categories
INSERT INTO public.challenge_categories (id, challenge_id, category, created_at) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Morning Run'), 'fitness', NOW() - INTERVAL '10 days'),
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Read a Book'), 'education', NOW() - INTERVAL '14 days'),
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Yoga Stretch'), 'wellness', NOW() - INTERVAL '5 days'),
    (uuid_generate_v4(), (SELECT id FROM public.challenges WHERE title = 'Push-Up Challenge'), 'strength', NOW() - INTERVAL '2 days');

-- Insert user saved posts
INSERT INTO public.user_saved_posts (user_id, post_id, created_at) VALUES
    ((SELECT id FROM public.users WHERE username = 'grace'), (SELECT id FROM public.posts WHERE content LIKE 'Just finished%'), NOW() - INTERVAL '6 hours'),
    ((SELECT id FROM public.users WHERE username = 'hank'), (SELECT id FROM public.posts WHERE content LIKE 'Morning yoga done%'), NOW() - INTERVAL '5 hours');

-- Insert notifications
INSERT INTO public.notifications (id, user_id, triggered_by_user_id, post_id, comment_id, type, message, is_read, created_at) VALUES
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'alice'), (SELECT id FROM public.users WHERE username = 'bob'), (SELECT id FROM public.posts WHERE content LIKE 'Just finished%'), NULL, 'comment', 'Bob commented on your run post', FALSE, NOW() - INTERVAL '23 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'bob'), (SELECT id FROM public.users WHERE username = 'eve'), NULL, (SELECT id FROM public.comments WHERE content LIKE 'Good luck%'), 'comment', 'Eve commented on your post', FALSE, NOW() - INTERVAL '19 hours'),
    (uuid_generate_v4(), (SELECT id FROM public.users WHERE username = 'dave'), (SELECT id FROM public.users WHERE username = 'iris'), (SELECT id FROM public.posts WHERE content LIKE 'Pushed out%'), NULL, 'like', 'Iris liked your push-up post', FALSE, NOW() - INTERVAL '9 hours');
