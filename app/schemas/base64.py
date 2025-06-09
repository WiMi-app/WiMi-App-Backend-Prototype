from pydantic import BaseModel
from typing import List

class Base64Images(BaseModel):
    base64_images: List[str]