import re
import hashlib
from rapidfuzz import fuzz


class DuplicateDetector:

    def __init__(self):
        pass

    # --------------------------------------------------
    # Normalize Question
    # --------------------------------------------------

    def normalize(self, text):

        if not text:
            return ""

        text = text.lower()

        # Normalize line endings
        text = text.replace("\r", "\n")

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common OCR artifacts
        text = text.replace("|", " ")
        text = text.replace("¦", " ")
        text = text.replace("•", " ")

        # Remove punctuation but preserve numbers,
        # letters and mathematical operators.
        text = re.sub(
            r"[^a-z0-9+\-*/=().,% ]",
            "",
            text
        )

        return text.strip()

    # --------------------------------------------------
    # Exact Hash
    # --------------------------------------------------

    def hash(self, text):

        normalized = self.normalize(text)

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    # --------------------------------------------------
    # Exact Duplicate
    # --------------------------------------------------

    def exact_duplicate(self, q1, q2):

        return self.hash(q1) == self.hash(q2)

    # --------------------------------------------------
    # Similarity Score
    # --------------------------------------------------

    def similarity(self, q1, q2):

        q1 = self.normalize(q1)
        q2 = self.normalize(q2)

        return fuzz.token_sort_ratio(q1, q2)

    # --------------------------------------------------
    # Duplicate Decision
    # --------------------------------------------------

    def is_duplicate(
        self,
        q1,
        q2,
        threshold=96
    ):

        return self.similarity(q1, q2) >= threshold