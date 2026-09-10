

import importlib.util
import os
from typing import Any, Dict, Optional

import pandas as pd

# Resolve paths correctly to the repo root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# app/services -> app -> backend -> project_root
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
MODEL_DIR = os.path.join(BASE_DIR, "ai", "nlp", "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
ENGINE_MODULE_PATH = os.path.join(BASE_DIR, "ai", "nlp", "compare_handles.py")


def _load_engine_class():
    """
    ai/nlp/ has no __init__.py, so it isn't an importable package --
    load compare_handles.py directly by file path instead of relying on
    sys.path/package structure.
    """
    spec = importlib.util.spec_from_file_location("decypher_compare_handles", ENGINE_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DeCypherAuthorshipEngine


class NLPStylometryService:
    def __init__(self):
        self.engine = None
        self.threshold = 0.65  # fallback default, only used if the real engine fails to load
        self._posts_df: Optional[pd.DataFrame] = None
        self._name_to_handle_id: Dict[str, str] = {}

        self._load_engine()
        self._load_posts_cache()

    def _load_engine(self):
        try:
            EngineClass = _load_engine_class()
            self.engine = EngineClass(model_dir=MODEL_DIR)
        except Exception as exc:
            # Fail soft: the service still starts (e.g. in an environment
            # missing the .joblib artifacts), it just falls back to a
            # weak heuristic in compare() below instead of crashing the app.
            print(f"[nlp_service] WARNING: could not load DeCypherAuthorshipEngine ({exc}). "
                  f"Falling back to a basic word-overlap heuristic -- this is NOT the validated model.")
            self.engine = None

    def _load_posts_cache(self):
        # posts.csv links posts to a handle via `handle_id` (e.g. "H00887"),
        # not a "handle"/"author" column. Build a name -> handle_id map from
        # handles.csv so callers can pass either the human-readable handle
        # name (what the rest of the API calls "handle") or a raw handle_id.
        posts_path = os.path.join(DATA_DIR, "posts.csv")
        handles_path = os.path.join(DATA_DIR, "handles.csv")
        if not os.path.exists(posts_path):
            return
        try:
            df = pd.read_csv(posts_path)
            handle_col = next((c for c in ("handle_id", "handle", "author") if c in df.columns), None)
            text_col = next((c for c in ("text", "content", "post") if c in df.columns), None)
            if not (handle_col and text_col):
                return

            posts_df = df[[handle_col, text_col]].dropna()
            posts_df = posts_df.rename(columns={handle_col: "_handle_id", text_col: "_content"})
            posts_df["_handle_id"] = posts_df["_handle_id"].astype(str)
            posts_df["_content"] = posts_df["_content"].astype(str)
            self._posts_df = posts_df

            if os.path.exists(handles_path):
                handles_df = pd.read_csv(handles_path)
                name_col = "handle_name" if "handle_name" in handles_df.columns else (
                    "handle" if "handle" in handles_df.columns else None
                )
                if name_col and "handle_id" in handles_df.columns:
                    self._name_to_handle_id = {
                        str(name).lower(): str(hid)
                        for name, hid in zip(handles_df[name_col], handles_df["handle_id"])
                        if pd.notna(name) and pd.notna(hid)
                    }
        except Exception:
            self._posts_df = None
            self._name_to_handle_id = {}

    def _get_posts_for_handle(self, handle: str) -> str:
        if self._posts_df is None or not handle:
            return ""
        lookup_id = self._name_to_handle_id.get(handle.lower(), handle)
        matched = self._posts_df[self._posts_df["_handle_id"] == str(lookup_id)]["_content"]
        return " \n ".join(matched.tolist())

    def compare(
        self,
        handle_a: str,
        handle_b: str,
        text_a: Optional[str] = None,
        text_b: Optional[str] = None,
    ) -> Dict[str, Any]:
        body_a = text_a if (text_a and text_a.strip()) else self._get_posts_for_handle(handle_a)
        body_b = text_b if (text_b and text_b.strip()) else self._get_posts_for_handle(handle_b)

        if not body_a or not body_b:
            return {
                "similarity_score": 0.0,
                "is_same_author": False,
                "confidence": 0.0,
                "shared_markers": [],
                "error": f"Insufficient sample text found for comparison between '{handle_a}' and '{handle_b}'.",
            }

        # Overlapping distinctive tokens (length >= 4) -- literal shared
        # vocabulary, a separate/complementary signal to the stylometric
        # model's output, kept for the API's shared_linguistic_markers field.
        tokens_a = {w.strip(",.?!;:\"'()[]{}") for w in body_a.lower().split() if len(w) >= 4}
        tokens_b = {w.strip(",.?!;:\"'()[]{}") for w in body_b.lower().split() if len(w) >= 4}
        markers = list(tokens_a & tokens_b)[:10]

        if self.engine is not None:
            result = self.engine.compare_texts(body_a, body_b)
            probability = result["same_author_probability"] / 100.0  # engine returns 0-100
            return {
                "similarity_score": round(probability, 4),
                "is_same_author": result["is_likely_match"],
                "confidence": round(probability if result["is_likely_match"] else 1 - probability, 4),
                "shared_markers": markers,
                "threshold_used": result["threshold_used"],
                "signals": result["signals"],            # evidence trail -- new, additive field
                "domain_routing": result["domain_routing"],  # new, additive field
            }

        # --- Fallback heuristic, only used if the trained engine failed to load ---
        words_a, words_b = set(body_a.lower().split()), set(body_b.lower().split())
        union = words_a | words_b
        score = float(len(words_a & words_b) / len(union)) if union else 0.0
        is_same = bool(score >= self.threshold)
        confidence = float(min(1.0, score + 0.05 if is_same else (1.0 - score)))
        return {
            "similarity_score": round(score, 4),
            "is_same_author": is_same,
            "confidence": round(confidence, 4),
            "shared_markers": markers,
            "threshold_used": self.threshold,
        }

    def check_contradiction(self, handle_id_a: str, handle_id_b: str, handles_df: pd.DataFrame) -> Dict[str, Any]:
        """De-confliction check, delegated to the engine when available."""
        if self.engine is not None:
            return self.engine.check_contradiction(handle_id_a, handle_id_b, handles_df)
        return {"contradiction_flag": False, "overlap_days": 0, "note": "Engine unavailable -- check skipped."}


nlp_service = NLPStylometryService()
