from fastapi import APIRouter

from app.api.v0 import auth, users, posts, likes, challenges, comments, notifications, follows

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(likes.router, prefix="/likes", tags=["likes"])
api_router.include_router(challenges.router, prefix="/challenges", tags=["challenges"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(follows.router, prefix="/follows", tags=["follows"])
