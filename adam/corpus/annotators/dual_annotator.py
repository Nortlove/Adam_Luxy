"""
Dual annotator for reviews (Phase 2+3 combined).

Scores a review BOTH as author self-expression (user-side, Domains 1-22)
AND as persuasion content for future readers (peer-ad-side, Domains 29-33 + 34).

Single Claude call, dual output — ~1.3x cost of single annotation instead of 2x.
"""

from __future__ import annotations

from typing import Any

from adam.corpus.annotators.base_annotator import BaseAnnotator
from adam.corpus.annotators.prompt_templates import (
    DUAL_SYSTEM_PROMPT as SYSTEM_PROMPT,
    DUAL_PROMPT_TEMPLATE,
    USER_ONLY_PROMPT_TEMPLATE,
)
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.models.peer_ad_annotation import PeerAdSideAnnotation


def _should_dual_annotate(review: dict[str, Any]) -> bool:
    """Determine if a review qualifies for peer-ad-side annotation."""
    helpful = review.get("helpful_vote", 0) or 0
    rating = review.get("rating", 3)
    text = review.get("text", "")
    text_len = len(text) if text else 0

    if helpful >= 1:
        return True
    if rating in (1, 5) and text_len > 200:
        return True
    return False


class DualAnnotator(BaseAnnotator):
    """Annotates reviews with user-side and optionally peer-ad-side."""

    def annotate(
        self, review: dict[str, Any], product_title: str = "", category: str = ""
    ) -> tuple[UserSideAnnotation, PeerAdSideAnnotation | None]:
        """Annotate a single review. Returns (user_side, peer_ad_side_or_None)."""
        review_text = review.get("text", "")
        if not review_text or len(review_text) < 20:
            review_id = self._make_review_id(review)
            return (
                UserSideAnnotation(review_id=review_id, annotation_confidence=0.0),
                None,
            )

        dual = _should_dual_annotate(review)
        review_id = self._make_review_id(review)

        if dual:
            return self._annotate_dual(review, review_id, product_title, category)
        else:
            return self._annotate_user_only(review, review_id, product_title, category)

    def _annotate_dual(
        self, review: dict, review_id: str, product_title: str, category: str
    ) -> tuple[UserSideAnnotation, PeerAdSideAnnotation]:
        prompt = DUAL_PROMPT_TEMPLATE.format(
            product_title=product_title[:200],
            category=category,
            star_rating=review.get("rating", 0),
            helpful_votes=review.get("helpful_vote", 0),
            review_text=review.get("text", "")[:3000],
        )

        result = self.call_claude_sync(SYSTEM_PROMPT, prompt)

        user_data = result.get("user_side", {})
        peer_data = result.get("peer_ad_side", {})
        conversion = result.get("conversion_outcome", "satisfied")

        user_ann = UserSideAnnotation(
            review_id=review_id,
            conversion_outcome=conversion,
            **user_data,
        )
        peer_ann = PeerAdSideAnnotation(
            review_id=review_id,
            **peer_data,
        )
        return user_ann, peer_ann

    def _annotate_user_only(
        self, review: dict, review_id: str, product_title: str, category: str
    ) -> tuple[UserSideAnnotation, None]:
        prompt = USER_ONLY_PROMPT_TEMPLATE.format(
            product_title=product_title[:200],
            category=category,
            star_rating=review.get("rating", 0),
            helpful_votes=review.get("helpful_vote", 0),
            review_text=review.get("text", "")[:3000],
        )

        result = self.call_claude_sync(SYSTEM_PROMPT, prompt)
        conversion = result.pop("conversion_outcome", "satisfied")

        user_ann = UserSideAnnotation(
            review_id=review_id,
            conversion_outcome=conversion,
            **result,
        )
        return user_ann, None

    @staticmethod
    def _make_review_id(review: dict) -> str:
        """Generate a deterministic review ID from user_id + asin + timestamp."""
        user_id = review.get("user_id", "unknown")
        asin = review.get("asin", "unknown")
        ts = review.get("timestamp", 0)
        return f"{user_id}_{asin}_{ts}"
