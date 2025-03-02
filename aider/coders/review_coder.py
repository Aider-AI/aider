from .review_prompts import ReviewPrompts
from .base_coder import Coder


class ReviewCoder(Coder):
    """Review code without making any changes."""

    edit_format = "review"
    gpt_prompts = ReviewPrompts()
