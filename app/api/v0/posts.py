from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from uuid import UUID

from app.schemas.posts import Post, PostCreate, PostUpdate
from app.schemas.users import User
from app.core.deps import get_current_active_user
from app.db.database import get_supabase
from app.util.supabase import (
    insert_into_supabase,
    get_from_supabase,
    update_supabase,
    delete_from_supabase
)

router = APIRouter()

@router.post("/", response_model=Post)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_supabase),
):
    now = datetime.now().isoformat()
    data = post_data.model_dump()
    data.update({
        "user_id": str(current_user.id),
        "created_at": now,
        "updated_at": now,
        "edited": False,
        "view_count": 0
    })
    created = insert_into_supabase(db, "posts", data)
    created["hashtags"] = []  # initialize empty hashtags list
    return Post(**created)


@router.get("/{post_id}", response_model=Post)
def read_post(
    post_id: UUID,
    db=Depends(get_supabase),
):
    post = get_from_supabase(db, "posts", match={"id": str(post_id)}, single=True)
    post["hashtags"] = []  # default empty list unless explicitly populated later
    return Post(**post)


@router.put("/{post_id}", response_model=Post)
def update_post(
    post_id: UUID,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_supabase),
):
    original = get_from_supabase(db, "posts", match={"id": str(post_id)}, single=True)

    if original["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this post")

    data = post_update.model_dump(exclude_unset=True)
    data.update({
        "updated_at": datetime.now().isoformat(),
        "edited": True
    })

    updated = update_supabase(db, "posts", data, {"id": str(post_id)})
    updated["hashtags"] = []  # default empty list
    return Post(**updated)


@router.delete("/{post_id}", response_model=dict)
def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_supabase),
):
    post = get_from_supabase(db, "posts", match={"id": str(post_id)}, single=True)

    if post["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    delete_from_supabase(db, "posts", {"id": str(post_id)})
    return {"status": "success", "message": "Post deleted"}
