"""Exact duplicate detection using SHA-256 hashing."""

import hashlib
import logging
from typing import List, Optional

from app.services.preprocessor import preprocess_text

logger = logging.getLogger(__name__)


def sha256_hash(text: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def check_exact_batch(
    texts: List[str],
    reference_texts: List[str],
) -> List[Optional[str]]:
    """Check each text against a list of reference texts using hash comparison.

    Returns a list of the same length as texts; each element is the matched
    reference text if an exact duplicate was found, otherwise None.
    """
    ref_map = {sha256_hash(preprocess_text(r)): r for r in reference_texts}
    results: List[Optional[str]] = []
    for text in texts:
        text_hash = sha256_hash(preprocess_text(text))
        results.append(ref_map.get(text_hash))
    return results
