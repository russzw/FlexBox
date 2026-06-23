"""Corporate Adapter Pipeline - automated CI/CD training data pipeline."""

from .pipeline import CorporatePipeline
from .sanitizer import SecretSanitizer

__all__ = ["CorporatePipeline", "SecretSanitizer"]
