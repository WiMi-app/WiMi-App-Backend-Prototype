# WiMi Backend

Backend for WiMi

## Getting Started

### Prerequisites

- Python 3.12
- Supabase account and project
- API keys for `.env`

### Installation

`bash setup.sh`

See the `schemas` file for the schema details.

### Running the Application

```
python run.py
```

The API will be available at http://localhost:8000.

API documentation is automatically generated at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### Database Schema Update

To update the database schema for the endorsement feature:

```
python scripts/update_db_endorsements.py
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login with username/email and password
- `POST /api/v1/auth/login/email`: Login with email and password

### Users
- `GET /api/v1/users/me`: Get current user info
- `PUT /api/v1/users/me`: Update current user info
- `GET /api/v1/users/{username}`: Get user by username
- `GET /api/v1/users/{username}/posts`: Get posts by username
- `POST /api/v1/users/follow`: Follow a user
- `DELETE /api/v1/users/unfollow/{user_id}`: Unfollow a user

### Posts
- `POST /api/v1/posts/`: Create a new post with a real-time photo
- `GET /api/v1/posts/`: Get all posts with optional filtering
- `GET /api/v1/posts/{post_id}`: Get a specific post
- `PUT /api/v1/posts/{post_id}`: Update a post
- `DELETE /api/v1/posts/{post_id}`: Delete a post
- `POST /api/v1/posts/save`: Save a post
- `DELETE /api/v1/posts/unsave/{post_id}`: Unsave a post

### Likes
- `POST /api/v1/likes/`: Like a post or comment
- `DELETE /api/v1/likes/post/{post_id}`: Unlike a post
- `DELETE /api/v1/likes/comment/{comment_id}`: Unlike a comment

### Endorsements
- `POST /api/v1/endorsements?post_id={post_id}`: Request endorsements for a post (automatically selects 3 random friends)
- `GET /api/v1/endorsements/post/{post_id}`: Get all endorsements for a post
- `GET /api/v1/endorsements/pending`: Get pending endorsement requests for the current user
- `PUT /api/v1/endorsements/{endorsement_id}`: Update an endorsement (endorse or decline with selfie)

## Post Endorsement System

The endorsement system adds a layer of authenticity verification to posts:

1. **Endorsement Request**: When a user creates a post, they can request endorsements from friends.
   - The system automatically selects 3 random mutual friends (users who follow each other).
   - Selected friends receive a notification about the endorsement request.

2. **Endorsement Process**:
   - Friends must take a selfie to endorse the post, verifying their identity.
   - Friends can either approve (with selfie) or decline the endorsement request.
   - All selfies taken by endorsers are linked to the post they endorse.

3. **Endorsement Status**:
   - A post is marked as "endorsed" when all three friends complete their endorsements.
   - Posts include endorsement information in their response, including count of endorsed and pending endorsements.

This feature helps ensure post authenticity by requiring verification from multiple trusted connections.

## User Management

### Deleting Users

The API includes an endpoint to delete users from both the `auth.users` and `public.users` tables:

```
DELETE /api/v0/users/{user_id}
```

This endpoint requires authentication, and users can only delete their own accounts.

To test this functionality, you can use the provided script:

```bash
# Delete your own account
python scripts/delete_user.py user@example.com password123

# Delete a specific user (if authorized)
python scripts/delete_user.py user@example.com password123 715ed5db-f090-4b8c-a067-640ecee36aa0
```

Note: This operation completely removes the user and all associated data from the system. This action cannot be undone.

