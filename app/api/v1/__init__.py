from fastapi import APIRouter

from app.api.v1 import auth, users, posts, likes, challenges, admin, moderation, recommendations

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(likes.router, prefix="/likes", tags=["likes"])
api_router.include_router(challenges.router, prefix="/challenges", tags=["challenges"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"]) 