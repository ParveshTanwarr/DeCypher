import os
import sys
import re
from typing import Any, Dict, Optional

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# backend/app/services
#       ↑
# backend/app
#       ↑
# backend
#       ↑
# project root
PROJECT_ROOT = os.path.abspath(
    os.path.join(CURRENT_DIR, "..", "..", "..")
)

AI_NLP_DIR = os.path.join(PROJECT_ROOT, "ai", "nlp")
MODEL_DIR = os.path.join(AI_NLP_DIR, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


# ============================================================
# LOAD THE PROVEN DECYPHER AUTHORSHIP ENGINE
# ============================================================

if AI_NLP_DIR not in sys.path:
    sys.path.insert(0, AI_NLP_DIR)

from compare_handles import DeCypherAuthorshipEngine


class NLPStylometryService:
    """
    Backend adapter around the production DeCypher authorship engine.

    The actual feature extraction and trained models live in:
        ai/nlp/compare_handles.py

    This service is intentionally thin. It:
      1. Loads the trained engine once.
      2. Loads posts.csv once.
      3. Accepts either handle IDs or human-readable handles.
      4. Returns the response format expected by /nlp/compare.
    """

    def __init__(self):
        self.engine: Optional[DeCypherAuthorshipEngine] = None
        self._posts_df: Optional[pd.DataFrame] = None
        self._handles_df: Optional[pd.DataFrame] = None
        self._name_to_handle_id: Dict[str, str] = {}

        self._load_engine()
        self._load_data()

    # ========================================================
    # ENGINE
    # ========================================================

    def _load_engine(self):
        """
        Load the complete trained DeCypher authorship engine.

        Unlike the previous implementation, this does NOT manually
        construct sparse TF-IDF features or truncate them to fit
        the classifier.
        """
        try:
            self.engine = DeCypherAuthorshipEngine(
                model_dir=MODEL_DIR
            )

            print("[NLP] DeCypher authorship engine loaded.")
            print(
                f"[NLP] Model directory: {MODEL_DIR}"
            )

        except Exception as exc:
            self.engine = None
            print(
                f"[NLP] WARNING: Failed to load authorship engine: {exc}"
            )

    # ========================================================
    # DATA
    # ========================================================

    def _load_data(self):
        """
        Load posts and handle metadata once at startup.
        """

        posts_path = os.path.join(DATA_DIR, "posts.csv")
        handles_path = os.path.join(DATA_DIR, "handles.csv")

        # ------------------------------
        # Posts
        # ------------------------------

        if os.path.exists(posts_path):
            try:
                posts_df = pd.read_csv(posts_path)

                if "handle_id" not in posts_df.columns:
                    raise ValueError(
                        "posts.csv is missing required column: handle_id"
                    )

                if "text" not in posts_df.columns:
                    raise ValueError(
                        "posts.csv is missing required column: text"
                    )

                posts_df = posts_df[
                    ["handle_id", "text"]
                ].dropna()

                posts_df["handle_id"] = (
                    posts_df["handle_id"].astype(str)
                )

                posts_df["text"] = (
                    posts_df["text"].astype(str)
                )

                self._posts_df = posts_df

                print(
                    f"[NLP] Loaded {len(posts_df)} posts."
                )

            except Exception as exc:
                self._posts_df = None
                print(
                    f"[NLP] WARNING: Failed to load posts.csv: {exc}"
                )

        # ------------------------------
        # Handles
        # ------------------------------

        if os.path.exists(handles_path):
            try:
                handles_df = pd.read_csv(handles_path)

                self._handles_df = handles_df

                name_col = None

                if "handle_name" in handles_df.columns:
                    name_col = "handle_name"
                elif "handle" in handles_df.columns:
                    name_col = "handle"

                if name_col and "handle_id" in handles_df.columns:
                    self._name_to_handle_id = {
                        str(name).lower(): str(handle_id)
                        for name, handle_id in zip(
                            handles_df[name_col],
                            handles_df["handle_id"],
                        )
                        if pd.notna(name)
                        and pd.notna(handle_id)
                    }

                print(
                    f"[NLP] Loaded {len(handles_df)} handle records."
                )

            except Exception as exc:
                self._handles_df = None
                self._name_to_handle_id = {}

                print(
                    f"[NLP] WARNING: Failed to load handles.csv: {exc}"
                )

    # ========================================================
    # HANDLE RESOLUTION
    # ========================================================

    def _resolve_handle_id(self, handle: str) -> str:
        """
        Accept either:

            H00887

        or:

            human-readable handle name

        and resolve it to the underlying handle ID when possible.
        """

        if not handle:
            return ""

        value = str(handle).strip()

        return self._name_to_handle_id.get(
            value.lower(),
            value,
        )

    # ========================================================
    # POSTS
    # ========================================================

    def _get_posts_for_handle(self, handle: str) -> str:
        """
        Concatenate all posts belonging to a handle.
        """

        if self._posts_df is None:
            return ""

        handle_id = self._resolve_handle_id(handle)

        matched = self._posts_df[
            self._posts_df["handle_id"] == str(handle_id)
        ]["text"]

        return "\n".join(
            matched.astype(str).tolist()
        )

    # ========================================================
    # SHARED LINGUISTIC MARKERS
    # ========================================================

    @staticmethod
    def _shared_markers(
        text_a: str,
        text_b: str,
    ):
        """
        Extract a small set of shared distinctive tokens.

        These are explanatory markers only. They are NOT used
        by the trained classifier.
        """

        tokens_a = {
            token
            for token in re.findall(
                r"\b[a-zA-Z0-9_]+\b",
                str(text_a).lower(),
            )
            if len(token) >= 4
        }

        tokens_b = {
            token
            for token in re.findall(
                r"\b[a-zA-Z0-9_]+\b",
                str(text_b).lower(),
            )
            if len(token) >= 4
        }

        shared = sorted(tokens_a & tokens_b)

        return shared[:10]

    # ========================================================
    # MAIN COMPARISON
    # ========================================================

    def compare(
        self,
        handle_a: str,
        handle_b: str,
        text_a: Optional[str] = None,
        text_b: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare two handles using the full DeCypher authorship
        engine.

        Raw text can optionally be supplied. If it is not supplied,
        posts.csv is used automatically.
        """

        if not handle_a or not handle_b:
            return {
                "similarity_score": 0.0,
                "is_same_author": False,
                "confidence": 0.0,
                "shared_markers": [],
                "error": "Both handle_a and handle_b are required.",
            }

        if self.engine is None:
            return {
                "similarity_score": 0.0,
                "is_same_author": False,
                "confidence": 0.0,
                "shared_markers": [],
                "error": (
                    "DeCypher authorship engine is unavailable."
                ),
            }

        # ----------------------------------------------------
        # Get text
        # ----------------------------------------------------

        body_a = (
            text_a.strip()
            if text_a and text_a.strip()
            else self._get_posts_for_handle(handle_a)
        )

        body_b = (
            text_b.strip()
            if text_b and text_b.strip()
            else self._get_posts_for_handle(handle_b)
        )

        if not body_a or not body_b:
            return {
                "similarity_score": 0.0,
                "is_same_author": False,
                "confidence": 0.0,
                "shared_markers": [],
                "error": (
                    "Insufficient sample text found for comparison "
                    f"between '{handle_a}' and '{handle_b}'."
                ),
            }

        # ----------------------------------------------------
        # Run the actual trained model
        # ----------------------------------------------------

        try:
            result = self.engine.compare_texts(
                body_a,
                body_b,
            )

        except Exception as exc:
            return {
                "similarity_score": 0.0,
                "is_same_author": False,
                "confidence": 0.0,
                "shared_markers": [],
                "error": (
                    f"Authorship comparison failed: {exc}"
                ),
            }

        # ----------------------------------------------------
        # Convert the engine's percentage probability into
        # the API's 0-1 similarity score.
        # ----------------------------------------------------

        probability_percent = float(
            result.get(
                "same_author_probability",
                0.0,
            )
        )

        similarity_score = max(
            0.0,
            min(
                1.0,
                probability_percent / 100.0,
            ),
        )

        is_same_author = bool(
            result.get(
                "is_likely_match",
                False,
            )
        )

        # ----------------------------------------------------
        # Confidence
        #
        # The engine already provides the model probability.
        # We use that probability directly as the confidence
        # exposed by this service.
        # ----------------------------------------------------

        confidence = similarity_score

        markers = self._shared_markers(
            body_a,
            body_b,
        )

        return {
            "similarity_score": round(
                similarity_score,
                4,
            ),
            "is_same_author": is_same_author,
            "confidence": round(
                confidence,
                4,
            ),
            "shared_markers": markers,
            "threshold_used": result.get(
                "threshold_used"
            ),
            "domain_routing": result.get(
                "domain_routing",
                {},
            ),
            "signals": result.get(
                "signals",
                {},
            ),
        }


# ============================================================
# SINGLETON SERVICE
# ============================================================

nlp_service = NLPStylometryService()