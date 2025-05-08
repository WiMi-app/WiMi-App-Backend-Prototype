-- Enable Row Level Security on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hashtags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_hashtags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_saved_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.challenge_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.challenge_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.challenge_achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.challenge_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.post_categories ENABLE ROW LEVEL SECURITY;

-- Users Table Policies
-- Anyone can view user profiles
CREATE POLICY "Users are viewable by everyone"
    ON public.users FOR SELECT
    USING (true);

-- Users can only update their own profile
CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

-- Posts Table Policies
-- Public posts are visible to everyone
CREATE POLICY "Public posts are viewable by everyone"
    ON public.posts FOR SELECT
    USING (NOT is_private OR user_id = auth.uid());

-- Private posts are only visible to the creator
CREATE POLICY "Private posts are only viewable by owner"
    ON public.posts FOR SELECT
    USING (NOT is_private OR user_id = auth.uid());

-- Users can only create their own posts
CREATE POLICY "Users can create their own posts"
    ON public.posts FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can only update their own posts
CREATE POLICY "Users can update their own posts"
    ON public.posts FOR UPDATE
    USING (user_id = auth.uid());

-- Users can only delete their own posts
CREATE POLICY "Users can delete their own posts"
    ON public.posts FOR DELETE
    USING (user_id = auth.uid());

-- Comments Table Policies
-- Comments on public posts are visible to everyone
CREATE POLICY "Comments on public posts are viewable by everyone"
    ON public.comments FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = comments.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
    );

-- Users can create comments on posts they can view
CREATE POLICY "Users can comment on viewable posts"
    ON public.comments FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = comments.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
        AND user_id = auth.uid()
    );

-- Users can only update their own comments
CREATE POLICY "Users can update their own comments"
    ON public.comments FOR UPDATE
    USING (user_id = auth.uid());

-- Users can only delete their own comments
CREATE POLICY "Users can delete their own comments"
    ON public.comments FOR DELETE
    USING (user_id = auth.uid());

-- Likes Table Policies
-- Anyone can view likes on public posts/comments
CREATE POLICY "Anyone can view likes on public content"
    ON public.likes FOR SELECT
    USING (
        (post_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = likes.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        ))
        OR
        (comment_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM public.comments
            JOIN public.posts ON comments.post_id = posts.id
            WHERE comments.id = likes.comment_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        ))
    );

-- Users can add likes to posts/comments they can view
CREATE POLICY "Users can like viewable content"
    ON public.likes FOR INSERT
    WITH CHECK (
        user_id = auth.uid() AND (
            (post_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM public.posts
                WHERE posts.id = likes.post_id
                AND (NOT posts.is_private OR posts.user_id = auth.uid())
            ))
            OR
            (comment_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM public.comments
                JOIN public.posts ON comments.post_id = posts.id
                WHERE comments.id = likes.comment_id
                AND (NOT posts.is_private OR posts.user_id = auth.uid())
            ))
        )
    );

-- Users can only delete their own likes
CREATE POLICY "Users can delete their own likes"
    ON public.likes FOR DELETE
    USING (user_id = auth.uid());

-- Follows Table Policies
-- Anyone can view follow relationships
CREATE POLICY "Follow relationships are viewable by everyone"
    ON public.follows FOR SELECT
    USING (true);

-- Users can only create their own follows
CREATE POLICY "Users can create their own follows"
    ON public.follows FOR INSERT
    WITH CHECK (follower_id = auth.uid());

-- Users can only delete their own follows
CREATE POLICY "Users can delete their own follows"
    ON public.follows FOR DELETE
    USING (follower_id = auth.uid());

-- Hashtags Table Policies
-- Anyone can view hashtags
CREATE POLICY "Hashtags are viewable by everyone"
    ON public.hashtags FOR SELECT
    USING (true);

-- Post Hashtags Junction Table Policies
-- Anyone can view post hashtags for visible posts
CREATE POLICY "Post hashtags are viewable for visible posts"
    ON public.post_hashtags FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = post_hashtags.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
    );

-- Users can add hashtags to their own posts
CREATE POLICY "Users can add hashtags to their own posts"
    ON public.post_hashtags FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = post_hashtags.post_id
            AND posts.user_id = auth.uid()
        )
    );

-- Users can remove hashtags from their own posts
CREATE POLICY "Users can remove hashtags from their own posts"
    ON public.post_hashtags FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = post_hashtags.post_id
            AND posts.user_id = auth.uid()
        )
    );

-- Notifications Table Policies
-- Users can only view their own notifications
CREATE POLICY "Users can view their own notifications"
    ON public.notifications FOR SELECT
    USING (user_id = auth.uid());

-- User Saved Posts Table Policies
-- Users can only see their own saved posts
CREATE POLICY "Users can view their own saved posts"
    ON public.user_saved_posts FOR SELECT
    USING (user_id = auth.uid());

-- Users can save public posts or their own posts
CREATE POLICY "Users can save viewable posts"
    ON public.user_saved_posts FOR INSERT
    WITH CHECK (
        user_id = auth.uid() AND
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = user_saved_posts.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
    );

-- Users can unsave their saved posts
CREATE POLICY "Users can unsave their saved posts"
    ON public.user_saved_posts FOR DELETE
    USING (user_id = auth.uid());

-- Challenges Table Policies
-- Anyone can view public challenges
CREATE POLICY "Public challenges are viewable by everyone"
    ON public.challenges FOR SELECT
    USING (NOT is_private OR creator_id = auth.uid());

-- Users can create their own challenges
CREATE POLICY "Users can create their own challenges"
    ON public.challenges FOR INSERT
    WITH CHECK (creator_id = auth.uid());

-- Users can update their own challenges
CREATE POLICY "Users can update their own challenges"
    ON public.challenges FOR UPDATE
    USING (creator_id = auth.uid());

-- Users can delete their own challenges
CREATE POLICY "Users can delete their own challenges"
    ON public.challenges FOR DELETE
    USING (creator_id = auth.uid());

-- Challenge Participants Table Policies
-- Anyone can view participants of public challenges
CREATE POLICY "Anyone can view participants of public challenges"
    ON public.challenge_participants FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_participants.challenge_id
            AND (NOT challenges.is_private OR challenges.creator_id = auth.uid())
        )
    );

-- Users can join public challenges
CREATE POLICY "Users can join public challenges"
    ON public.challenge_participants FOR INSERT
    WITH CHECK (
        user_id = auth.uid() AND
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_participants.challenge_id
            AND (NOT challenges.is_private OR challenges.creator_id = auth.uid())
        )
    );

-- Users can update their own participation status
CREATE POLICY "Users can update their own participation status"
    ON public.challenge_participants FOR UPDATE
    USING (user_id = auth.uid());

-- Users can leave challenges
CREATE POLICY "Users can leave challenges"
    ON public.challenge_participants FOR DELETE
    USING (user_id = auth.uid());

-- Challenge Posts Junction Table Policies
-- Anyone can view challenge posts for visible challenges
CREATE POLICY "Challenge posts are viewable for visible challenges"
    ON public.challenge_posts FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_posts.challenge_id
            AND (NOT challenges.is_private OR challenges.creator_id = auth.uid())
        )
        AND
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = challenge_posts.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
    );

-- Users can add their posts to challenges they participate in
CREATE POLICY "Users can add posts to participated challenges"
    ON public.challenge_posts FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = challenge_posts.post_id
            AND posts.user_id = auth.uid()
        )
        AND
        (
            EXISTS (
                SELECT 1 FROM public.challenges
                WHERE challenges.id = challenge_posts.challenge_id
                AND challenges.creator_id = auth.uid()
            )
            OR
            EXISTS (
                SELECT 1 FROM public.challenge_participants
                WHERE challenge_participants.challenge_id = challenge_posts.challenge_id
                AND challenge_participants.user_id = auth.uid()
            )
        )
    );

-- Users can remove their posts from challenges
CREATE POLICY "Users can remove their posts from challenges"
    ON public.challenge_posts FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = challenge_posts.post_id
            AND posts.user_id = auth.uid()
        )
    );

-- Challenge Achievements Table Policies
-- Users can view achievements for challenges they participate in
CREATE POLICY "Users can view achievements for relevant challenges"
    ON public.challenge_achievements FOR SELECT
    USING (
        user_id = auth.uid()
        OR
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_achievements.challenge_id
            AND challenges.creator_id = auth.uid()
        )
    );

-- Challenge Categories Table Policies
-- Anyone can view categories of public challenges
CREATE POLICY "Anyone can view categories of public challenges"
    ON public.challenge_categories FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_categories.challenge_id
            AND (NOT challenges.is_private OR challenges.creator_id = auth.uid())
        )
    );

-- Challenge creators can manage challenge categories
CREATE POLICY "Challenge creators can manage challenge categories"
    ON public.challenge_categories FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.challenges
            WHERE challenges.id = challenge_categories.challenge_id
            AND challenges.creator_id = auth.uid()
        )
    );

-- Post Categories Table Policies
-- Anyone can view categories of visible posts
CREATE POLICY "Anyone can view categories of visible posts"
    ON public.post_categories FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = post_categories.post_id
            AND (NOT posts.is_private OR posts.user_id = auth.uid())
        )
    );

-- Post creators can manage post categories
CREATE POLICY "Post creators can manage post categories"
    ON public.post_categories FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.posts
            WHERE posts.id = post_categories.post_id
            AND posts.user_id = auth.uid()
        )
    );
