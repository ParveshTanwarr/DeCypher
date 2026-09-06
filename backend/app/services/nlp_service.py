import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import hstack

# Resolve paths correctly to the repo root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# app/services -> app -> backend -> project_root
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
MODEL_DIR = os.path.join(BASE_DIR, "ai", "nlp", "models")
DATA_DIR = os.path.join(BASE_DIR, "data")


class NLPStylometryService:
    def __init__(self):
        self.char_vectorizer = None
        self.word_vectorizer = None
        self.expert_model = None
        self.threshold = 0.65
        self._posts_df: Optional[pd.DataFrame] = None
        self._name_to_handle_id: Dict[str, str] = {}
        self._load_models()
        self._load_posts_cache()

    def _load_models(self):
        char_vec_path = os.path.join(MODEL_DIR, "pan20_character_vectorizer.joblib")
        word_vec_path = os.path.join(MODEL_DIR, "pan20_word_vectorizer.joblib")
        model_path = os.path.join(MODEL_DIR, "decypher_expert_model.joblib")
        thresh_path = os.path.join(MODEL_DIR, "model_thresholds.npz")

        if os.path.exists(char_vec_path):
            self.char_vectorizer = joblib.load(char_vec_path)
        if os.path.exists(word_vec_path):
            self.word_vectorizer = joblib.load(word_vec_path)
        if os.path.exists(model_path):
            self.expert_model = joblib.load(model_path)
        if os.path.exists(thresh_path):
            try:
                data = np.load(thresh_path)
                if "threshold" in data:
                    self.threshold = float(data["threshold"])
            except Exception:
                pass

    def _load_posts_cache(self):
        # posts.csv links posts to a handle via `handle_id` (e.g. "H00887"),
        # not a "handle"/"author" column -- the old detection here never
        # matched, so _posts_df stayed None and every compare() fell
        # through to "Insufficient sample text" unless raw text was passed
        # in directly.
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

            # posts.csv is keyed by handle_id, but callers naturally think
            # in terms of the human-readable handle name (that's what the
            # rest of the API calls "handle" everywhere else) -- so build a
            # name -> handle_id map from handles.csv and accept either.
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
        # Accept either a human-readable handle name or a raw handle_id.
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
                "error": f"Insufficient sample text found for comparison between '{handle_a}' and '{handle_b}'."
            }

        # Sparse Vector Extraction
        if self.char_vectorizer and self.word_vectorizer:
            c_vec_a = self.char_vectorizer.transform([body_a])
            c_vec_b = self.char_vectorizer.transform([body_b])
            w_vec_a = self.word_vectorizer.transform([body_a])
            w_vec_b = self.word_vectorizer.transform([body_b])

            feat_a = hstack([c_vec_a, w_vec_a])
            feat_b = hstack([c_vec_b, w_vec_b])

            if self.expert_model and hasattr(self.expert_model, "predict_proba"):
                # Use trained classifier if available
                diff_feat = np.abs(feat_a - feat_b)

                if hasattr(diff_feat, "toarray"):
                    diff_feat = diff_feat.toarray()

                if diff_feat.shape[1] != self.expert_model.n_features_in_:
                    diff_feat = diff_feat[:, :self.expert_model.n_features_in_]

                score = float(self.expert_model.predict_proba(diff_feat)[0][1])
            else:
                sim_matrix = cosine_similarity(feat_a, feat_b)
                score = float(max(0.0, min(1.0, sim_matrix[0][0])))
        else:
            # Fallback heuristic: word set Jaccard
            words_a = set(body_a.lower().split())
            words_b = set(body_b.lower().split())
            union = words_a | words_b
            score = float(len(words_a & words_b) / len(union)) if union else 0.0

        is_same = bool(score >= self.threshold)
        confidence = float(min(1.0, score + 0.05 if is_same else (1.0 - score)))

        # Overlapping distinctive tokens (length >= 4)
        tokens_a = {w.strip(",.?!;:\"'()[]{}") for w in body_a.lower().split() if len(w) >= 4}
        tokens_b = {w.strip(",.?!;:\"'()[]{}") for w in body_b.lower().split() if len(w) >= 4}
        markers = list(tokens_a & tokens_b)[:10]

        return {
            "similarity_score": round(score, 4),
            "is_same_author": is_same,
            "confidence": round(confidence, 4),
            "shared_markers": markers,
            "threshold_used": self.threshold
        }


nlp_service = NLPStylometryService()