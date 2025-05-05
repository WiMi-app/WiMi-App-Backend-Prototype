# WiMi Social Media Backend

A production-ready FastAPI and Supabase-based backend for a social media application.

## Features

- **User Authentication**: Registration, login, JWT-based token authentication
- **User Profiles**: Update profile information, follow/unfollow users
- **Posts**: Create, read, update, delete posts
- **Real-Time Photo Posting**: Posts require photos captured in real-time, not from photo albums
- **Social Interactions**: Like/unlike posts and comments
- **Hashtags**: Automatic hashtag extraction from post content
- **Saved Posts**: Save and unsave posts for later viewing

## Tech Stack

- FastAPI: Modern, high-performance web framework
- Supabase: Open source Firebase alternative with PostgreSQL
- Pydantic: Data validation and settings management
- JWT Authentication: Secure authentication mechanism

## Getting Started

### Prerequisites

- Python 3.12
- Supabase account and project
- PostgreSQL database (provided by Supabase)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/wimi-social-backend.git
   cd wimi-social-backend
   ```

2. Create a virtual environment:
   ```
   python12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables in `.env` file

### Running the Application

```
uvicorn app.main:app --reload
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

```

## Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in your environment variables
2. Use a production ASGI server like Uvicorn with Gunicorn:
   ```
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```
3. Set up HTTPS using a reverse proxy like Nginx

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI documentation
- Supabase documentation
- Pydantic documentation 