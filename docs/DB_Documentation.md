# Social Media Database Schema Documentation

## Overview

This document outlines the database schema for a social media platform built using Supabase. The schema is designed to support core social media functionality including user profiles, posts, comments, likes, follows, hashtags, notifications, direct messaging, challenges, and recommendation systems.

## Database Tables

### Users

**Table Name: public.users**  
Stores user account information and profile details.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| username | VARCHAR(255) | Unique username for identification |
| full\_name | VARCHAR(255) | User's full name |
| bio | TEXT | User's profile description |
| avatar\_url | TEXT | URL to profile picture |
| updated\_at | TIMESTAMP | Last profile update timestamp |

**Constraints:** \- username and email must be unique

### Posts

**Table Name: public.posts**  
Contains content created and shared by users.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| user\_id | UUID | Reference to creator (Foreign key to users.id) |
| content | TEXT | Post text content |
| media\_urls | TEXT\[\] | Array of media attachment URLs |
| location | TEXT | Optional location tag |
| is\_private | BOOLEAN | Whether post is private (default: false) |
| created\_at | TIMESTAMP | Post creation timestamp |
| updated\_at | TIMESTAMP | Last edit timestamp |
| edited | BOOLEAN | Whether post has been edited (default: false) |
| challenge\_id | UUID | Foreign Key |
| is_endorsed | BOOLEAN | Whether post is endorsed (default: false) |

**Relationships:** \- user\_id references users(id) with CASCADE delete

### Comments

**Table Name: public.comments**  
User comments on posts, supporting nested replies.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| post\_id | UUID | Reference to parent post |
| user\_id | UUID | Reference to comment author |
| content | TEXT | Comment text content |
| parent\_comment\_id | UUID | Reference to parent comment (for nested replies) |
| created\_at | TIMESTAMP | Comment creation timestamp |

**Relationships:** \- post\_id references posts(id) with CASCADE delete \- user\_id references users(id) with CASCADE delete \- parent\_comment\_id references comments(id) with CASCADE delete

### Likes

**Table Name: public.likes**  
Tracks user likes on both posts and comments.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| user\_id | UUID | User who created the like |
| post\_id | UUID | Reference to liked post (nullable) |
| comment\_id | UUID | Reference to liked comment (nullable) |
| created\_at | TIMESTAMP | Like creation timestamp |

**Constraints:** \- Either post\_id OR comment\_id must be filled (not both) \- Unique constraint prevents duplicate likes

**Relationships:** \- user\_id references users(id) with CASCADE delete \- post\_id references posts(id) with CASCADE delete \- comment\_id references comments(id) with CASCADE delete

### 

### Follows

**Table Name: public.follows**  
Represents follow relationships between users.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| follower\_id | UUID | User who is following |
| followed\_id | UUID | User who is being followed |
| created\_at | TIMESTAMP | Follow creation timestamp |

**Constraints:** \- Unique constraint prevents duplicate follows \- Check constraint prevents self-follows

**Relationships:** \- follower\_id references users(id) with CASCADE delete \- followed\_id references users(id) with CASCADE delete

### Post Endorsements

**Table Name: public.post_endorsements**  
Tracks endorsement requests and statuses for posts.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| post\_id | UUID | Reference to endorsed post |
| endorser\_id | UUID | User who has been requested to endorse the post |
| status | VARCHAR(50) | Endorsement status ('pending', 'endorsed', 'declined') |
| selfie\_url | TEXT | URL to the selfie image taken for endorsement (nullable) |
| created\_at | TIMESTAMP | When endorsement was created |
| endorsed\_at | TIMESTAMP | When endorsement was completed (nullable) |

**Constraints:** \- Unique constraint on (post\_id, endorser\_id) |

**Relationships:** \- post\_id references posts(id) with CASCADE delete \- endorser\_id references users(id) with CASCADE delete

### Hashtags

**Table Name: public.hashtags**  
Stores unique hashtags used throughout the platform.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| name | VARCHAR(255) | Unique hashtag text |
| usage\_count | INTEGER | No. times used |
| created\_at | TIMESTAMP | Creation timestamp |

**Constraints:** \- name must be unique

### Notifications

**Table Name: public.notifications**  
System notifications for user activities. \[ This is pushed to external service \] 

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| user\_id | UUID | User receiving the notification |
| triggered\_by\_user\_id | UUID | User who triggered the notification (nullable) |
| post\_id | UUID | Related post, if applicable (nullable) |
| comment\_id | UUID | Related comment, if applicable (nullable) |
| type | VARCHAR(50) | Notification type (like, comment, follow, etc.) |
| message | TEXT | Notification message content |
| is\_read | BOOLEAN | Whether notification has been read (default: false) |
| created\_at | TIMESTAMP | Creation timestamp |

**Relationships:** \- user\_id references users(id) with CASCADE delete \- triggered\_by\_user\_id references users(id) with SET NULL on delete \- post\_id references posts(id) with CASCADE delete \- comment\_id references comments(id) with CASCADE delete

### User Saved Posts

**Table Name: public.user\_saved\_posts**  
Tracks posts that users have saved/bookmarked.

| Column | Type | Description |
| :---- | :---- | :---- |
| user\_id | UUID | User who saved the post |
| post\_id | UUID | Saved post reference |
| created\_at | TIMESTAMP | When post was saved |

**Relationships:** \- user\_id references users(id) with CASCADE delete \- post\_id references posts(id) with CASCADE delete \- Composite primary key (user\_id, post\_id)

### Challenges

**Table Name: public.challenges**  
User-created challenges with specific criteria.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| creator\_id | UUID | Reference to challenge creator |
| title | VARCHAR(255) | Challenge title |
| description | TEXT | Challenge description |
| due\_date | TIMESTAMP WITH TIME ZONE | Challenge end date |
| location | TEXT | Optional location requirement |
| restriction | TEXT | Additional challenge restrictions |
| repetition | ENUM | Repetition pattern ('daily', 'weekly', 'monthly', 'custom', 'none') |
| repetition\_frequency | INTEGER | Frequency (e.g., 3 for "every 3 days") |
| repetition\_days | INTEGER\[\] | For weekly challenges: \[1,3,5\] for Mon,Wed,Fri |
| check\_in\_time | TIME | Time of day for check-ins |
| created\_at | TIMESTAMP WITH TIME ZONE | Challenge creation timestamp |
| updated\_at | TIMESTAMP WITH TIME ZONE | Last update timestamp |
| is\_private | BOOLEAN | Whether challenge is private (default: FALSE) |
| time\_window | INTEGER | Grace period for challenge post |

**Relationships:** \- creator\_id references users(id) with CASCADE delete

### Challenge Participants

**Table Name: public.challenge\_participants**  
Users who join challenges.

| Column | Type | Description |
| :---- | :---- | :---- |
| challenge\_id | UUID | Reference to challenge |
| user\_id | UUID | Reference to participant |
| joined\_at | TIMESTAMP WITH TIME ZONE | When user joined the challenge |
| status | VARCHAR(50) | Participation status ('active', 'completed', 'dropped') |

**Relationships:** \- challenge\_id references challenges(id) with CASCADE delete \- user\_id references users(id) with CASCADE delete \- Composite primary key (challenge\_id, user\_id)

### 

### Challenge Achievements

**Table Name: public.challenge\_achievements**  
Track completion milestones in challenges.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| challenge\_id | UUID | Reference to challenge |
| user\_id | UUID | Reference to user |
| achievement\_type | ENUM | Type (success\_rate, 'completion') |
| description | TEXT | Achievement description |
| achieved\_at | TIMESTAMP WITH TIME ZONE | When achieved |
| success\_count | INTEGER | For streak achievements |

**Constraints:** \- Unique constraint on (challenge\_id, user\_id, achievement\_type)

**Relationships:** \- challenge\_id references challenges(id) with CASCADE delete \- user\_id references users(id) with CASCADE delete

### 

###  Challenge Categories

**Table Name: public.challenge\_categories**  
Tags challenges with categories for content-based recommendations.

| Column | Type | Description |
| :---- | :---- | :---- |
| id | UUID | Primary key, automatically generated |
| challenge\_id | UUID | Reference to challenge |
| category | VARCHAR(100) | Category name |
| created\_at | TIMESTAMP WITH TIME ZONE | Creation timestamp |

**Constraints:** \- Unique constraint on (challenge\_id, category)

**Relationships:** \- challenge\_id references challenges(id) with CASCADE delete

## 

## Database Indexes

The following indexes optimize query performance:

| Index Name | Table | Column(s) |
| :---- | :---- | :---- |
| idx\_posts\_user\_id | posts | user\_id |
| idx\_comments\_post\_id | comments | post\_id |
| idx\_comments\_user\_id | comments | user\_id |
| idx\_follows\_follower\_id | follows | follower\_id |
| idx\_follows\_followed\_id | follows | followed\_id |
| idx\_notifications\_user\_id | notifications | user\_id |
| idx\_challenges\_creator\_id | challenges | creator\_id |
| idx\_challenge\_participants\_challenge\_id | challenge\_participants | challenge\_id |
| idx\_challenge\_participants\_user\_id | challenge\_participants | user\_id |
| idx\_challenge\_posts\_challenge\_id | challenge\_posts | challenge\_id |
| idx\_challenge\_achievements\_challenge\_id | challenge\_achievements | challenge\_id |
| idx\_challenge\_achievements\_user\_id | challenge\_achievements | user\_id  |
| idx\_posts\_challenge\_id | posts | challenge\_id |
| idx\_post\_endorsements\_post\_id | post_endorsements | post\_id |
| idx\_post\_endorsements\_endorser\_id | post_endorsements | endorser\_id |

