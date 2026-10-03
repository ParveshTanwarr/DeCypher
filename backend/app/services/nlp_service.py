

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


def _load_engine_module():
    """Load the shared feature implementation without changing its model contract."""
    spec = importlib.util.spec_from_file_location("decypher_compare_handles", ENGINE_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load NLP feature module: {ENGINE_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_engine_class():
    return _load_engine_module().DeCypherAuthorshipEngine


class NLPStylometryService:
    def __init__(self):
        self.engine = None
        self.feature_module = None
        self.engine_status = "unavailable"
        self.engine_error = None
        self.threshold = 0.65  # fallback default, only used if the real engine fails to load
        self._posts_df: Optional[pd.DataFrame] = None
        self._name_to_handle_ids: Dict[str, list] = {}
        self._known_handle_ids: set[str] = set()
        self._handles_df: Optional[pd.DataFrame] = None

        self._load_engine()
        self._load_posts_cache()

    def _load_engine(self):
        try:
            self.feature_module = _load_engine_module()
            EngineClass = self.feature_module.DeCypherAuthorshipEngine
            self.engine = EngineClass(model_dir=MODEL_DIR)
            self.engine_status = "validated_model"
            self.engine_error = None
        except Exception as exc:
            # Fail soft: the service still starts (e.g. in an environment
            # missing the .joblib artifacts), it just falls back to a
            # weak heuristic in compare() below instead of crashing the app.
            print(f"[nlp_service] WARNING: could not load DeCypherAuthorshipEngine ({exc}). "
                  f"Falling back to a basic word-overlap heuristic -- this is NOT the validated model.")
            self.engine = None
            self.engine_status = "fallback_heuristic"
            self.engine_error = str(exc)

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

            timestamp_col = next(
                (column for column in ("timestamp", "created_at", "posted_at", "published_at", "date") if column in df.columns),
                None,
            )
            selected_columns = [handle_col, text_col] + ([timestamp_col] if timestamp_col else [])
            posts_df = df[selected_columns].dropna(subset=[handle_col, text_col]).copy()
            posts_df = posts_df.rename(columns={handle_col: "_handle_id", text_col: "_content"})
            posts_df["_handle_id"] = posts_df["_handle_id"].astype(str)
            posts_df["_content"] = posts_df["_content"].astype(str)
            if timestamp_col:
                posts_df = posts_df.rename(columns={timestamp_col: "_timestamp"})
                posts_df["_timestamp"] = pd.to_datetime(posts_df["_timestamp"], errors="coerce", utc=True)
            else:
                posts_df["_timestamp"] = pd.NaT
            self._posts_df = posts_df
            self._known_handle_ids = set(posts_df["_handle_id"].astype(str))

            if os.path.exists(handles_path):
                handles_df = pd.read_csv(handles_path)
                self._handles_df = handles_df
                name_col = "handle_name" if "handle_name" in handles_df.columns else (
                    "handle" if "handle" in handles_df.columns else None
                )
                if name_col and "handle_id" in handles_df.columns:
                    name_to_ids: Dict[str, list] = {}
                    for name, hid in zip(handles_df[name_col], handles_df["handle_id"]):
                        if pd.notna(name) and pd.notna(hid):
                            name_to_ids.setdefault(str(name).strip().lower(), []).append(str(hid))
                    self._name_to_handle_ids = name_to_ids
        except Exception:
            self._posts_df = None
            self._name_to_handle_ids = {}
            self._known_handle_ids = set()
            self._handles_df = None

    def _resolve_handle_id(self, handle: str) -> Optional[str]:
        if not handle:
            return None
        raw = str(handle).strip()
        if raw in self._known_handle_ids:
            return raw
        ids = self._name_to_handle_ids.get(raw.lower(), [])
        return ids[0] if len(ids) == 1 else None

    def _get_posts_for_handle(self, handle: str) -> str:
        if self._posts_df is None or not handle:
            return ""
        lookup_id = self._resolve_handle_id(handle)
        if not lookup_id:
            return ""
        matched = self._posts_df[self._posts_df["_handle_id"] == str(lookup_id)]["_content"]
        return " \n ".join(matched.tolist())

    def activity_profile(self, handles: list[str]) -> Dict[str, Any]:
        """Summarize timestamped posting activity when source timestamps exist."""
        empty = {
            "available": False,
            "has_post_timestamps": False,
            "timestamped_post_count": 0,
            "profiled_handle_count": 0,
            "per_handle": [],
            "note": "No usable per-post timestamps were supplied by the source dataset.",
        }
        if self._posts_df is None or not handles or "_timestamp" not in self._posts_df.columns:
            return empty

        rows = []
        total = 0
        for handle in handles:
            handle_id = self._resolve_handle_id(handle)
            if not handle_id:
                continue
            matched = self._posts_df[self._posts_df["_handle_id"] == str(handle_id)]
            timestamps = matched["_timestamp"].dropna().sort_values()
            if timestamps.empty:
                continue
            gaps = timestamps.diff().dropna().dt.total_seconds() / 3600.0
            hours = timestamps.dt.hour.value_counts().sort_index()
            weekdays = timestamps.dt.day_name().value_counts()
            rows.append({
                "handle": handle,
                "timestamped_post_count": int(len(timestamps)),
                "first_post_at": timestamps.iloc[0].isoformat(),
                "last_post_at": timestamps.iloc[-1].isoformat(),
                "active_days": int(timestamps.dt.date.nunique()),
                "posts_by_utc_hour": {str(int(k)): int(v) for k, v in hours.items()},
                "posts_by_weekday": {str(k): int(v) for k, v in weekdays.items()},
                "median_inter_post_interval_hours": (
                    round(float(gaps.median()), 3) if not gaps.empty else None
                ),
            })
            total += len(timestamps)

        if not rows:
            return empty
        return {
            "available": True,
            "has_post_timestamps": True,
            "timestamped_post_count": int(total),
            "profiled_handle_count": len(rows),
            "per_handle": rows,
            "timezone": "UTC",
            "note": "Descriptive posting activity from source timestamps; it is not a behavioural identity proof.",
        }

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
                "engine_status": self.engine_status,
                "fallback_used": self.engine is None,
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
                "engine_status": self.engine_status,
                "fallback_used": False,
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
            "engine_status": self.engine_status,
            "fallback_used": True,
            "engine_warning": "Validated authorship model unavailable; this score is a basic word-overlap heuristic.",
        }

    def profile_handles(self, handles: list[str]) -> Dict[str, Any]:
        """Aggregate the repository's trained stylometry feature schema by handle.

        Raw post text is never returned or persisted in the behavioural profile.
        """
        empty = {
            "available": False,
            "sample_post_count": 0,
            "profiled_handle_count": 0,
            "engine_status": self.engine_status,
            "fallback_used": self.engine is None,
            "features": {},
            "per_handle": [],
        }
        if self._posts_df is None or not handles or self.feature_module is None:
            return empty

        feature_names = [
            "word_count", "character_count", "average_word_length",
            "word_length_std", "unique_words", "type_token_ratio", "hapax_ratio",
            "long_word_ratio", "short_word_ratio", "average_sentence_length",
            "sentence_length_std", "median_sentence_length", "max_sentence_length",
            "period_rate", "comma_rate", "exclamation_rate", "question_rate",
            "semicolon_rate", "colon_rate", "dash_rate", "quote_rate",
            "repeated_punctuation", "repeated_character_runs", "capitalization_ratio",
            "digit_rate", "function_word_rate", "emoji_rate", "typo_pattern_rate",
        ]
        rows = []
        handle_mean_vectors = []
        weighted_feature_sum = None
        weighted_post_total = 0
        total_posts = 0
        function_words = getattr(self.feature_module, "FUNCTION_WORDS", set())

        for handle in handles:
            handle_id = self._resolve_handle_id(handle)
            if not handle_id:
                continue
            matched = self._posts_df[self._posts_df["_handle_id"] == str(handle_id)]["_content"]
            texts = [str(value) for value in matched.tolist() if str(value).strip()]
            if not texts:
                continue
            vectors = [self.feature_module.style_features(value) for value in texts]
            if not vectors:
                continue
            import numpy as np
            matrix = np.vstack(vectors)
            mean_vector = matrix.mean(axis=0)
            token_lists = [self.feature_module.words(value) for value in texts]
            tokens = [token for group in token_lists for token in group]
            token_counts = {}
            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            top_terms = sorted(
                ((term, count) for term, count in token_counts.items() if len(term) >= 4),
                key=lambda item: (-item[1], item[0]),
            )[:8]
            rows.append({
                "handle": handle,
                "post_count": len(texts),
                "features": {
                    name: round(float(mean_vector[index]), 5)
                    for index, name in enumerate(feature_names)
                },
                "top_terms": [{"term": term, "count": count} for term, count in top_terms],
            })
            handle_mean_vectors.append(mean_vector)
            if weighted_feature_sum is None:
                weighted_feature_sum = mean_vector * len(texts)
            else:
                weighted_feature_sum += mean_vector * len(texts)
            weighted_post_total += len(texts)
            total_posts += len(texts)


        if weighted_feature_sum is None or not handle_mean_vectors:
            return empty

        post_weighted = weighted_feature_sum / weighted_post_total
        handle_weighted = np.vstack(handle_mean_vectors).mean(axis=0)
        return {
            "available": True,
            "sample_post_count": total_posts,
            "profiled_handle_count": len(rows),
            "engine_status": self.engine_status,
            "fallback_used": self.engine is None,
            "features": {
                name: round(float(post_weighted[index]), 5)
                for index, name in enumerate(feature_names)
            },
            "handle_mean_features": {
                name: round(float(handle_weighted[index]), 5)
                for index, name in enumerate(feature_names)
            },
            "per_handle": rows,
            "aggregation_method": "post_weighted",
            "method": "Per-post style_features from the same feature implementation used by the trained authorship engine. Actor-level features are weighted by each handle's number of profiled posts; handle_mean_features preserves the equal-weighted mean across handle profiles.",
            "function_word_vocabulary_size": len(function_words),
        }

    def check_contradiction(self, handle_a: str, handle_b: str) -> Dict[str, Any]:
        """Run the model de-confliction check using bundled handle metadata."""
        if self.engine is None:
            return {"contradiction_flag": False, "overlap_days": 0, "note": "Engine unavailable -- check skipped."}
        if self._handles_df is None:
            return {"contradiction_flag": False, "overlap_days": 0, "note": "Handle metadata unavailable -- check skipped."}

        handle_id_a = self._resolve_handle_id(handle_a)
        handle_id_b = self._resolve_handle_id(handle_b)
        if not handle_id_a or not handle_id_b:
            return {"contradiction_flag": False, "overlap_days": 0, "note": "Could not resolve both handles for de-confliction."}

        try:
            return self.engine.check_contradiction(handle_id_a, handle_id_b, self._handles_df)
        except (KeyError, IndexError, ValueError) as exc:
            return {"contradiction_flag": False, "overlap_days": 0, "note": f"De-confliction check skipped: {exc}"}

# Shared service instance used by the correlation and NLP routers.
nlp_service = NLPStylometryService()
