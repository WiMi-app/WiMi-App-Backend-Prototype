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

