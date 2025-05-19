from datetime import datetime
from typing import Dict, Optional, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.schemas.auth import Token
from app.schemas.challenges import (ChallengeBase, 
                                    ChallengeCreate, ChallengeOut,
                                    ChallengeParticipantOut, ChallengeUpdate)
from app.schemas.comments import CommentCreate, CommentOut
from app.schemas.endorsements import (EndorsementCreate, EndorsementOut,
                                      EndorsementStatus, EndorsementUpdate)
from app.schemas.follows import FollowCreate, FollowOut
from app.schemas.hashtags import HashtagOut
from app.schemas.likes import LikeCreate, LikeOut
from app.schemas.notifications import (NotificationOut, NotificationStatus,
                                       NotificationType)
from app.schemas.posts import PostCreate, PostOut, PostUpdate, SavedPostCreate
from app.schemas.users import UserBase, UserOut, UserUpdate

# Export the models for easy access
__all__ = [
    "Token", "TokenData",
    "UserBase", "UserOut", "UserUpdate",
    "PostCreate", "PostOut", "PostUpdate", "SavedPostCreate",
    "CommentCreate", "CommentOut",
    "LikeCreate", "LikeOut",
    "FollowCreate", "FollowOut","HashtagOut",
    "NotificationOut", "NotificationStatus", "NotificationType",
    "ChallengeBase", "ChallengeCreate", "ChallengeOut", "ChallengeUpdate",
    "ChallengeParticipantOut",
    "EndorsementCreate", "EndorsementOut", "EndorsementUpdate", "EndorsementStatus"
]