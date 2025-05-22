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

## Deploying to Google Cloud Run

Follow these steps to deploy the application to Google Cloud Run:

1. Make sure you have the Google Cloud SDK installed and configured:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. Build and push the Docker image to Google Container Registry:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/wimi-backend
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy wimi-backend \
     --image gcr.io/YOUR_PROJECT_ID/wimi-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars="ENVIRONMENT=production" \
     --set-env-vars="PORT=8080"
   ```

4. Set required environment variables:
   - In the Google Cloud Console, go to Cloud Run
   - Select your service
   - Click "Edit & Deploy New Revision"
   - Add all required environment variables (SUPABASE_URL, SUPABASE_KEY, JWT_SECRET, etc.)

> **Note**: For production, consider using Secret Manager for sensitive environment variables.

## Media Storage Buckets

The application uses Supabase Storage for media files, organized in three buckets:

1. **avatars**: User profile images
   - Uploads automatically organized by user ID
   - Endpoints: `/api/v0/users/me/avatar` (file upload) and `/api/v0/users/me/avatar/base64` (base64 upload)

2. **post_media**: Images and media for posts
   - Uploads organized by user ID
   - Endpoints: `/api/v0/posts/media` (file upload) and `/api/v0/posts/media/base64` (base64 upload)
   - Create posts with media using `/api/v0/posts/with-media`

3. **endorsements**: Selfie verification images for post endorsements
   - Organized by endorsement ID and user ID
   - Upload when endorsing: `/api/v0/endorsements/{endorsement_id}` (with form data)
   - Separate selfie uploads: `/api/v0/endorsements/{endorsement_id}/selfie` (file) and `/api/v0/endorsements/{endorsement_id}/selfie/base64` (base64)

### Media Upload Limits

- Maximum upload size: 20MB per file
- Supported formats: JPEG, PNG, GIF
- All uploads require authentication
- Old media is automatically deleted when replaced

## API Endpoints

### Authentication
- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login with username/email and password
- `POST /api/v1/auth/login/email`: Login with email and password

### Users
- `GET /api/v1/users/me`: Get current user info
- `PUT /api/v1/users/me`: Update current user info
- `POST /api/v1/users/me/avatar`: Upload user avatar (file upload)
- `POST /api/v1/users/me/avatar/base64`: Upload user avatar (base64)
- `GET /api/v1/users/{username}`: Get user by username
- `GET /api/v1/users/{username}/posts`: Get posts by username
- `POST /api/v1/users/follow`: Follow a user
- `DELETE /api/v1/users/unfollow/{user_id}`: Unfollow a user

### Posts
- `POST /api/v1/posts/`: Create a new post with a real-time photo
- `POST /api/v1/posts/with-media`: Create a post with uploaded media files
- `POST /api/v1/posts/media`: Upload media files for posts
- `POST /api/v1/posts/media/base64`: Upload base64 encoded media for posts
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
- `POST /api/v1/endorsements/{endorsement_id}/selfie`: Upload a selfie for an endorsement
- `POST /api/v1/endorsements/{endorsement_id}/selfie/base64`: Upload a base64 encoded selfie for an endorsement

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

