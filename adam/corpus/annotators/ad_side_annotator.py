"""
Ad-side annotator for product descriptions (Phase 1).

Scores product descriptions against Domains 29-33 + evolutionary/implicit targets.
"""

from __future__ import annotations

from typing import Any

from adam.corpus.annotators.base_annotator import BaseAnnotator
from adam.corpus.annotators.prompt_templates import (
    AD_SIDE_SYSTEM_PROMPT as SYSTEM_PROMPT,
    AD_SIDE_USER_PROMPT_TEMPLATE as USER_PROMPT_TEMPLATE,
)
from adam.corpus.models.ad_side_annotation import AdSideAnnotation


class AdSideAnnotator(BaseAnnotator):
    """Annotates product descriptions against ad-side taxonomy."""

    def annotate(self, product: dict[str, Any]) -> AdSideAnnotation:
        """Annotate a single product description. Returns AdSideAnnotation."""
        title = product.get("title", "")
        category = product.get("main_category", "")
        price = product.get("price", "unknown")
        brand = product.get("store", "") or product.get("brand", "")
        description = " ".join(product.get("description", []))
        features = " ".join(product.get("features", []))
        asin = product.get("parent_asin", product.get("asin", ""))

        # Build text for annotation — use whatever is available
        desc_text = description or features or title
        feat_text = features if description else ""

        if not desc_text or len(desc_text) < 10:
            # Not enough text to annotate — return defaults
            return AdSideAnnotation(asin=asin, annotation_confidence=0.0)

        prompt = USER_PROMPT_TEMPLATE.format(
            title=title[:200],
            category=category,
            price=price,
            brand=brand,
            description_text=desc_text[:2000],
            features_text=feat_text[:1000],
        )

        result = self.call_claude_sync(SYSTEM_PROMPT, prompt)
        return AdSideAnnotation(asin=asin, **result)

    async def annotate_async(self, product: dict[str, Any]) -> AdSideAnnotation:
        """Async version for concurrent annotation."""
        title = product.get("title", "")
        category = product.get("main_category", "")
        price = product.get("price", "unknown")
        brand = product.get("store", "") or product.get("brand", "")
        description = " ".join(product.get("description", []))
        features = " ".join(product.get("features", []))
        asin = product.get("parent_asin", product.get("asin", ""))

        desc_text = description or features or title
        feat_text = features if description else ""

        if not desc_text or len(desc_text) < 10:
            return AdSideAnnotation(asin=asin, annotation_confidence=0.0)

        prompt = USER_PROMPT_TEMPLATE.format(
            title=title[:200],
            category=category,
            price=price,
            brand=brand,
            description_text=desc_text[:2000],
            features_text=feat_text[:1000],
        )

        result = await self.call_claude(SYSTEM_PROMPT, prompt)
        return AdSideAnnotation(asin=asin, **result)
