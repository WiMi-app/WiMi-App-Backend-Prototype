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

- Python 3.9 or higher
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
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your environment variables in `.env` file:
   ```
   SUPABASE_URL=https://your-supabase-url.supabase.co
   SUPABASE_KEY=your-supabase-key
   DATABASE_URL=postgresql://postgres:your-password@your-supabase-url.supabase.co:5432/postgres
   SECRET_KEY=your-secret-key-for-jwt
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   APP_NAME=WiMi-Social
   APP_VERSION=0.1.0
   ENVIRONMENT=development
   ```

### Database Setup

The application expects the following tables in your Supabase database:

- users
- posts
- comments
- likes
- follows
- hashtags
- post_hashtags
- notifications
- messages
- user_saved_posts

See the `models.py` file for the schema details.

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

## Real-Time Photo Posting

WiMi enforces real-time photo posting, meaning users can only post photos taken in the moment rather than from their photo album or gallery. This encourages authentic, in-the-moment sharing.

### How It Works

1. When a user takes a photo in the app, the client captures metadata including:
   - Precise capture timestamp
   - Device information
   - Camera information
   - Optional location data

2. This metadata is sent along with the post content to the server.

3. The server validates that:
   - The `is_real_time` flag is set to true
   - The photo's capture timestamp is within 60 seconds of the current time

4. If validation passes, the post is created with the real-time photo. If validation fails, the request is rejected.

### API Request Example

```json
POST /api/v1/posts/

{
  "content": "Beautiful sunset! #nofilter",
  "media_urls": ["https://example.com/image.jpg"],
  "location": "San Francisco, CA",
  "is_private": false,
  "is_real_time": true,
  "image_metadata": {
    "capture_timestamp": "2023-08-15T19:45:30.123456",
    "device_info": {
      "model": "iPhone 12",
      "os": "iOS 15.5",
      "app_version": "1.2.3"
    },
    "camera_info": {
      "resolution": "12MP",
      "camera_type": "back"
    },
    "location_data": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "accuracy": 10.0
    }
  }
}
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