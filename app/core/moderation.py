import logging
from enum import Enum
from typing import Dict, Tuple
from fastapi import HTTPException, status
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

class ModerationCategory(str, Enum):
    """Categories of content that may be flagged by the moderation API."""
    HARASSMENT = "harassment"
    HARASSMENT_THREATENING = "harassment/threatening" 
    HATE = "hate"
    HATE_THREATENING = "hate/threatening"
    SELF_HARM = "self-harm"
    SELF_HARM_INTENT = "self-harm/intent"
    SELF_HARM_INSTRUCTIONS = "self-harm/instructions"
    SEXUAL = "sexual"
    SEXUAL_MINORS = "sexual/minors"
    VIOLENCE = "violence"
    VIOLENCE_GRAPHIC = "violence/graphic"


async def moderate_content(
    content: str, 
    raise_exception: bool = False,
    content_type: str = "post"
) -> Tuple[bool, Dict]:
    """
    Check if content violates OpenAI's content policy using the Moderation API.
    
    This function checks content to identify potentially harmful or illegal content,
    including:
    - Hate speech or discriminatory content
    - Violence or threats
    - Self-harm content
    - Sexual or inappropriate content
    - Content encouraging dangerous or illegal activities
    
    Args:
        content: Text content to moderate
        raise_exception: Whether to raise an HTTPException if content is flagged
        content_type: Type of content (for error messages)
        
    Returns:
        Tuple[bool, Dict]: 
            - First element is True if content is safe, False otherwise
            - Second element is a dictionary containing moderation results:
              'flagged' (bool), 
              'flagged_categories' (List[str]), 
              'category_scores' (Dict[str, float]),
              and optionally 'error' (str) if moderation failed.
            
    Raises:
        HTTPException: If content is flagged and raise_exception is True
    """
    if not content or not content.strip():
        return True, {
            "flagged": False,
            "flagged_categories": [],
            "category_scores": {}
        }
        
    try:
        client = OpenAI(api_key=settings.OPENAI_KEY)
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=content,
        )
        
        # Get results from the first item (there's only one in our case)
        results_data = response.results[0]
        
        # Check if content is flagged
        is_flagged = results_data.flagged
        
        output_details = {
            "flagged": is_flagged,
            "flagged_categories": [],
            "category_scores": vars(results_data.category_scores)
        }
        
        if is_flagged:
            flagged_categories_list = []
            # Find categories that were flagged by iterating through the boolean category flags
            for category_name, category_is_flagged in vars(results_data.categories).items():
                if category_is_flagged:
                    flagged_categories_list.append(category_name)
            output_details["flagged_categories"] = flagged_categories_list
            
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": f"The {content_type} content was flagged as inappropriate and cannot be published.",
                        "reason": "Content moderation detected potentially harmful or inappropriate material.",
                        "flagged_categories": flagged_categories_list
                    }
                )
                
            return False, output_details
        
        return True, output_details # Content is safe, return details including scores
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in content moderation: {str(e)}", exc_info=True)
        
        error_details = {
            "flagged": True, # If moderation system fails, treat as not safe by default
            "flagged_categories": ["moderation_system_error"],
            "category_scores": {},
            "error": f"Content moderation API error: {str(e)}"
        }
        
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error checking content: {str(e)}"
            )
            
        return False, error_details # Indicate not safe if moderation system itself fails


async def moderate_challenge(challenge_description: str, raise_exception: bool = True) -> bool:
    """
    Moderate a challenge description.
    
    Checks if the challenge description contains:
    - Content encouraging dangerous activities
    - Threats or intent to harm others
    - Content that violates legal boundaries
    - Inappropriate or harmful instructions
    
    Args:
        challenge_description: Description text of the challenge
        raise_exception: Whether to raise exceptions for flagged content
        
    Returns:
        bool: True if the challenge passes moderation, False otherwise
        
    Raises:
        HTTPException: If content is flagged and raise_exception is True
    """
    is_safe, _ = await moderate_content(
        challenge_description, 
        raise_exception=raise_exception,
        content_type="challenge"
    )
    return is_safe


async def moderate_post(post_content: str, raise_exception: bool = True) -> bool:
    """
    Moderate a post's content.
    
    Checks if the post content contains:
    - Hate speech or discriminatory language
    - Threats or intent to harm others
    - Content that violates legal boundaries
    - Inappropriate or harmful material
    
    Args:
        post_content: Content of the post
        raise_exception: Whether to raise exceptions for flagged content
        
    Returns:
        bool: True if the post passes moderation, False otherwise
        
    Raises:
        HTTPException: If content is flagged and raise_exception is True
    """
    is_safe, _ = await moderate_content(
        post_content, 
        raise_exception=raise_exception,
        content_type="post"
    )
    return is_safe 