import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from scipy.spatial.distance import cosine

# Resolve paths relative to project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
MODEL_DIR = os.path.join(BASE_DIR, "ai", "nlp", "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

class NLPStylometryService:
    def __init__(self):
        self.char_vectorizer = None
        self.word_vectorizer = None
        self.expert_model = None
        self.threshold = 0.65
        self._load_models()

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
            data = np.load(thresh_path)
            if "threshold" in data:
                self.threshold = float(data["threshold"])

    def _get_posts_for_handle(self, handle: str) -> str:
        posts_path = os.path.join(DATA_DIR, "posts.csv")
        if not os.path.exists(posts_path):
            return ""

        df = pd.read_csv(posts_path)
        handle_col = "handle" if "handle" in df.columns else ("author" if "author" in df.columns else None)
        text_col = "content" if "content" in df.columns else ("post" if "post" in df.columns else "text")

        if not handle_col or text_col not in df.columns:
            return ""

        matched = df[df[handle_col].str.lower() == handle.lower()][text_col].dropna()
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

        # Vector extraction
        if self.char_vectorizer and self.word_vectorizer:
            c_vec_a = self.char_vectorizer.transform([body_a]).toarray()[0]
            c_vec_b = self.char_vectorizer.transform([body_b]).toarray()[0]
            w_vec_a = self.word_vectorizer.transform([body_a]).toarray()[0]
            w_vec_b = self.word_vectorizer.transform([body_b]).toarray()[0]

            feat_a = np.hstack([c_vec_a, w_vec_a])
            feat_b = np.hstack([c_vec_b, w_vec_b])

            # Cosine similarity
            cosine_sim = 1.0 - cosine(feat_a, feat_b) if (np.any(feat_a) and np.any(feat_b)) else 0.0
            score = float(max(0.0, min(1.0, cosine_sim)))
        else:
            # Fallback heuristic: word set Jaccard
            words_a = set(body_a.lower().split())
            words_b = set(body_b.lower().split())
            union = words_a | words_b
            score = float(len(words_a & words_b) / len(union)) if union else 0.0

        is_same = bool(score >= self.threshold)
        confidence = float(min(1.0, score + 0.05 if is_same else (1.0 - score)))

        # Find overlapping tokens of length >= 4
        tokens_a = set([w.strip(",.?!;:") for w in body_a.lower().split() if len(w) >= 4])
        tokens_b = set([w.strip(",.?!;:") for w in body_b.lower().split() if len(w) >= 4])
        markers = list(tokens_a & tokens_b)[:10]

        return {
            "similarity_score": round(score, 4),
            "is_same_author": is_same,
            "confidence": round(confidence, 4),
            "shared_markers": markers,
            "threshold_used": self.threshold
        }

nlp_service = NLPStylometryService()