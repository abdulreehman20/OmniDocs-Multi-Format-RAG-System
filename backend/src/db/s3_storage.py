"""Neon Object Storage (S3-compatible) client.

Phase 0: protocol and fake live in `src.providers`. Real boto3 implementation lands in Phase 1.
"""

from src.providers.protocols import ObjectStorage

__all__ = ["ObjectStorage"]
