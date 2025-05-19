# Row Level Security (RLS) Policies

This document outlines the Row Level Security (RLS) policies implemented in the WiMi application's Supabase database. RLS provides fine-grained access control at the row level, ensuring that users can only access the data they are authorized to see.

## Overview

Row Level Security is enabled on all tables in the database to ensure proper data isolation and secure access patterns. These policies determine:

- Which users can view specific data
- Who can create new records
- Who can update existing records
- Who can delete records

## Tables with RLS Enabled

- `users` - User profiles
- `posts` - User posts
- `comments` - Post comments
- `likes` - Post and comment likes
- `follows` - User follow relationships
- `hashtags` - Post hashtags
- `post_hashtags` - Junction table linking posts to hashtags
- `notifications` - User notifications
- `user_saved_posts` - Users' saved posts
- `challenges` - User challenges
- `challenge_participants` - Challenge participation
- `challenge_posts` - Posts linked to challenges
- `challenge_achievements` - User achievements in challenges
- `challenge_categories` - Challenge categories
- `post_categories` - Post categories
- `post_endorsements` - Post endorsement system

## Detailed RLS Policies

### Users Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Users are viewable by everyone | SELECT | Anyone can view user profiles |
| Users can update own profile | UPDATE | Users can only update their own profiles |
| Service can create users | INSERT | Service role can create new users during signup |

### Posts Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Public posts are viewable by everyone | SELECT | Everyone can view non-private posts |
| Private posts are only viewable by owner | SELECT | Only post creators can view their private posts |
| Users can create their own posts | INSERT | Users can only create posts as themselves |
| Users can update their own posts | UPDATE | Users can only edit posts they created |
| Users can delete their own posts | DELETE | Users can only delete posts they created |

### Comments Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Comments on public posts are viewable by everyone | SELECT | Anyone can see comments on non-private posts |
| Users can comment on viewable posts | INSERT | Users can comment on posts they can see |
| Users can update their own comments | UPDATE | Users can edit only their own comments |
| Users can delete their own comments | DELETE | Users can delete only their own comments |

### Likes Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Anyone can view likes on public content | SELECT | Like counts visible for public posts/comments |
| Users can like viewable content | INSERT | Users can like posts/comments they can see |
| Users can delete their own likes | DELETE | Users can remove their own likes |

### Follows Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Follow relationships are viewable by everyone | SELECT | Anyone can see who follows whom |
| Users can create their own follows | INSERT | Users can follow others, but only as themselves |
| Users can delete their own follows | DELETE | Users can unfollow others they're following |

### Hashtags Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Hashtags are viewable by everyone | SELECT | Anyone can view hashtags |

### Post Hashtags Junction Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Post hashtags are viewable for visible posts | SELECT | Hashtags visible for posts user can view |
| Users can add hashtags to their own posts | INSERT | Only post creators can tag their posts |
| Users can remove hashtags from their own posts | DELETE | Only post creators can untag their posts |

### Notifications Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Users can view their own notifications | SELECT | Users see only their own notifications |

### User Saved Posts Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Users can view their own saved posts | SELECT | Users see only posts they've saved |
| Users can save viewable posts | INSERT | Users can save posts they can see |
| Users can unsave their saved posts | DELETE | Users can remove posts from saved list |

### Challenges Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Public challenges are viewable by everyone | SELECT | Anyone can see non-private challenges |
| Users can create their own challenges | INSERT | Users can create challenges as themselves |
| Users can update their own challenges | UPDATE | Only challenge creators can edit them |
| Users can delete their own challenges | DELETE | Only challenge creators can delete them |

### Challenge Participants Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Anyone can view participants of public challenges | SELECT | Participation visible for public challenges |
| Users can join public challenges | INSERT | Users can join visible challenges |
| Users can update their own participation status | UPDATE | Users can change their participation status |
| Users can leave challenges | DELETE | Users can remove themselves from challenges |

### Challenge Posts Junction Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Challenge posts are viewable for visible challenges | SELECT | Posts visible for challenges user can see |
| Users can add posts to participated challenges | INSERT | Users can link posts to challenges they're in |
| Users can remove their posts from challenges | DELETE | Users can unlink their posts from challenges |

### Challenge Achievements Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Users can view achievements for relevant challenges | SELECT | Users see achievements for challenges they're involved in |

### Challenge Categories Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Anyone can view categories of public challenges | SELECT | Categories visible for public challenges |
| Challenge creators can manage challenge categories | ALL | Only creators can add/edit/delete categories |

### Post Categories Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Anyone can view categories of visible posts | SELECT | Categories visible for viewable posts |
| Post creators can manage post categories | ALL | Only post creators can manage categories |

### Post Endorsements Table

| Policy | Operation | Description |
|--------|-----------|-------------|
| Endorsements are viewable for public posts | SELECT | Anyone can see endorsements on public posts |
| Users can create endorsement requests for their own posts | INSERT | Only post owners can request endorsements |
| Endorsers can update their own endorsements | UPDATE | Users can respond to endorsement requests |
| Post owners can delete endorsement requests | DELETE | Only post owners can cancel endorsement requests |

## Best Practices for Working with RLS

1. **Always use authenticated endpoints**: Ensure API endpoints properly use the authenticated user context.

2. **Include proper filtering**: When querying data in your application, include filters that respect RLS policies.

3. **Test policy combinations**: Verify that multiple policies on the same table work together correctly.

4. **Avoid bypassing RLS**: Never use service roles in client-side code as they bypass RLS entirely.

5. **Check RLS policies when debugging**: If data access issues occur, verify that RLS policies allow the intended access pattern.

## Implementation Details

The RLS policies are implemented in SQL and applied to the database during initialization. The actual SQL implementation can be found in `scripts/v0/rls.sql`.

### Example Policy Implementation

```sql
-- Example of a basic RLS policy
CREATE POLICY "Users can only update their own profile"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);
```

This policy ensures that users can only update their own profile records by checking if the authenticated user ID (`auth.uid()`) matches the `id` field of the record being updated. 