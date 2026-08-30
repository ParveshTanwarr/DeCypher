"""
ShadowTrace / DeCypher — AI/NLP integration module.

This is the hand-off contract for the Backend Lead. It wraps the trained
Step 6.17 domain-aware authorship pipeline (decypher_expert_model.joblib +
pan20_expert_model.joblib + domain_detector_model.joblib) into a single
function:

    compare_handles(handle_id_a, handle_id_b, posts_df) -> dict

Feature extraction here is copied EXACTLY from step_6_17_domain_aware.py so
predictions are consistent with what the models were trained on. Do not
change the feature functions independently of that script.

Required files (same directory, or pass a custom `model_dir`):
    pan20_character_vectorizer.joblib
    pan20_word_vectorizer.joblib
    domain_vectorizer.joblib
    pan20_expert_model.joblib
    decypher_expert_model.joblib
    domain_detector_model.joblib
    model_thresholds.npz
"""

import os
import re
import joblib
import numpy as np
import pandas as pd

# ============================================================
# FEATURE EXTRACTION (copied from step_6_17_domain_aware.py —
# keep in sync with that file; do not edit independently)
# ============================================================

FUNCTION_WORDS = {
    "the", "a", "an", "and", "or", "but",
    "if", "then", "because", "so",
    "although", "while", "with", "without",
    "for", "from", "to", "of", "in", "on",
    "at", "by", "is", "are", "was", "were",
    "be", "been", "being", "i", "you",
    "he", "she", "we", "they", "it",
    "my", "your", "his", "her", "our",
    "their"
}


def normalize(text):
    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words(text):
    return re.findall(r"\b\w+\b", normalize(text))


def style_features(text):
    text = str(text)
    lower = text.lower()
    ws = re.findall(r"\b\w+\b", lower)
    n_words = len(ws)
    n_chars = max(len(text), 1)

    if n_words:
        lengths = np.array([len(w) for w in ws], dtype=float)
        avg_word_len = lengths.mean()
        word_std = lengths.std()
        unique = len(set(ws))
        ttr = unique / n_words
        long_ratio = np.mean(lengths >= 8)
        short_ratio = np.mean(lengths <= 3)
    else:
        avg_word_len = word_std = unique = ttr = long_ratio = short_ratio = 0

    freq = {}
    for w in ws:
        freq[w] = freq.get(w, 0) + 1
    hapax = sum(v == 1 for v in freq.values()) / max(unique, 1)

    sentences = re.split(r"[.!?]+", text)
    sentence_lengths = []
    for s in sentences:
        sw = re.findall(r"\b\w+\b", s)
        if sw:
            sentence_lengths.append(len(sw))

    if sentence_lengths:
        sl = np.array(sentence_lengths, dtype=float)
        avg_sentence = sl.mean()
        sentence_std = sl.std()
        median_sentence = np.median(sl)
        max_sentence = sl.max()
    else:
        avg_sentence = sentence_std = median_sentence = max_sentence = 0

    period = text.count(".")
    comma = text.count(",")
    exclamation = text.count("!")
    question = text.count("?")
    semicolon = text.count(";")
    colon = text.count(":")
    dash = text.count("-")
    quote = text.count("'") + text.count('"')

    upper = sum(c.isupper() for c in text)
    lower_count = sum(c.islower() for c in text)
    capitalization = upper / max(upper + lower_count, 1)

    digits = sum(c.isdigit() for c in text)
    function_count = sum(freq.get(w, 0) for w in FUNCTION_WORDS)
    emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF]", text))
    repeated_punctuation = len(re.findall(r"([!?.,;:])\1+", text))
    repeated_chars = len(re.findall(r"(.)\1{2,}", lower))
    typo_count = len(re.findall(r"\b\w*(\w)\1\1\w*\b", lower))

    return np.array([
        n_words, n_chars,
        avg_word_len, word_std,
        unique, ttr, hapax,
        long_ratio, short_ratio,
        avg_sentence, sentence_std, median_sentence, max_sentence,
        period / n_chars, comma / n_chars, exclamation / n_chars,
        question / n_chars, semicolon / n_chars, colon / n_chars,
        dash / n_chars, quote / n_chars,
        repeated_punctuation, repeated_chars,
        capitalization,
        digits / n_chars,
        function_count / max(n_words, 1),
        emoji_count / max(n_words, 1),
        typo_count / max(n_words, 1),
    ])


def pair_style_features(data):
    output = []
    for a, b in zip(data["text1"], data["text2"]):
        f1 = style_features(a)
        f2 = style_features(b)
        diff = np.abs(f1 - f2)
        denominator = np.abs(f1) + np.abs(f2) + 1e-9
        relative = diff / denominator
        maximum = np.maximum(np.abs(f1), np.abs(f2))
        minimum = np.minimum(np.abs(f1), np.abs(f2))
        ratio = minimum / (maximum + 1e-9)
        average = (f1 + f2) / 2
        output.append(np.concatenate([diff, relative, ratio, average]))
    return np.nan_to_num(np.array(output), nan=0, posinf=0, neginf=0)


def tfidf_pair_features(data, vectorizer):
    v1 = vectorizer.transform(data["text1"])
    v2 = vectorizer.transform(data["text2"])
    cosine = v1.multiply(v2).sum(axis=1).A1
    difference = np.abs(v1 - v2)
    diff_mean = np.asarray(difference.mean(axis=1)).ravel()
    shared = np.asarray(v1.multiply(v2).getnnz(axis=1)).ravel()
    nnz1 = np.asarray(v1.getnnz(axis=1)).ravel()
    nnz2 = np.asarray(v2.getnnz(axis=1)).ravel()
    shared_ratio = shared / np.maximum(np.maximum(nnz1, nnz2), 1)
    return np.column_stack([cosine, diff_mean, shared, shared_ratio])


def token_features(data):
    output = []
    for a, b in zip(data["text1"], data["text2"]):
        w1, w2 = words(a), words(b)
        s1, s2 = set(w1), set(w2)
        intersection = s1 & s2
        union = s1 | s2
        jaccard = len(intersection) / max(len(union), 1)
        c1 = len(intersection) / max(len(s1), 1)
        c2 = len(intersection) / max(len(s2), 1)
        length_ratio = min(len(w1), len(w2)) / max(max(len(w1), len(w2)), 1)
        char1, char2 = len(str(a)), len(str(b))
        char_ratio = min(char1, char2) / max(max(char1, char2), 1)
        output.append([jaccard, c1, c2, min(c1, c2), max(c1, c2), length_ratio, char_ratio])
    return np.array(output, dtype=np.float32)


def build_features(data, char_vectorizer, word_vectorizer):
    style = pair_style_features(data)
    char = tfidf_pair_features(data, char_vectorizer)
    word = tfidf_pair_features(data, word_vectorizer)
    token = token_features(data)
    return np.hstack([style, char, word, token])


# ============================================================
# MODEL BUNDLE
# ============================================================

class DeCypherAuthorshipEngine:
    """Loads all trained artifacts once; call .compare_handles() repeatedly."""

    def __init__(self, model_dir="."):
        self.char_vectorizer = joblib.load(os.path.join(model_dir, "pan20_character_vectorizer.joblib"))
        self.word_vectorizer = joblib.load(os.path.join(model_dir, "pan20_word_vectorizer.joblib"))
        self.domain_vectorizer = joblib.load(os.path.join(model_dir, "domain_vectorizer.joblib"))
        self.pan_model = joblib.load(os.path.join(model_dir, "pan20_expert_model.joblib"))
        self.dec_model = joblib.load(os.path.join(model_dir, "decypher_expert_model.joblib"))
        self.domain_model = joblib.load(os.path.join(model_dir, "domain_detector_model.joblib"))

        thresholds = np.load(os.path.join(model_dir, "model_thresholds.npz"))
        self.pan_threshold = float(thresholds["pan_threshold"])
        self.dec_threshold = float(thresholds["dec_threshold"])

    def _domain_weight(self, text1, text2):
        """Router: is this pair more PAN-style or Decypher-style? Blend accordingly."""
        docs = pd.Series([text1, text2]).astype(str)
        scores = self.domain_model.predict_proba(self.domain_vectorizer.transform(docs))[:, 1]
        return float(scores.mean())  # 0 = PAN-like, 1 = Decypher-like

    def _predict_raw(self, text1, text2):
        data = pd.DataFrame({"text1": [text1], "text2": [text2]})
        X = build_features(data, self.char_vectorizer, self.word_vectorizer)

        pan_prob = float(self.pan_model.predict_proba(X)[:, 1][0])
        dec_prob = float(self.dec_model.predict_proba(X)[:, 1][0])
        dec_weight = self._domain_weight(text1, text2)
        pan_weight = 1.0 - dec_weight

        total = pan_weight + dec_weight
        pan_weight, dec_weight = pan_weight / total, dec_weight / total
        final_prob = pan_weight * pan_prob + dec_weight * dec_prob

        return final_prob, pan_prob, dec_prob, dec_weight

    def compare_texts(self, text1, text2):
        """Core entry point: compare two raw text blobs directly."""
        final_prob, pan_prob, dec_prob, domain_weight = self._predict_raw(text1, text2)

        f1, f2 = style_features(text1), style_features(text2)
        # index reference (style_features order): [n_words,n_chars,avg_word_len,word_std,
        # unique,ttr,hapax,long_ratio,short_ratio,avg_sentence,sentence_std,median_sentence,
        # max_sentence,period_rate,comma_rate,excl_rate,q_rate,semi_rate,colon_rate,dash_rate,
        # quote_rate,repeated_punct,repeated_chars,capitalization,digit_rate,function_word_rate,
        # emoji_rate,typo_rate]
        signals = {
            "sentence_length_match": bool(abs(f1[9] - f2[9]) < 2.5),
            "punctuation_style_match": bool(abs(f1[13] - f2[13]) < 0.01 and abs(f1[15] - f2[15]) < 0.01),
            "function_word_usage_match": bool(abs(f1[25] - f2[25]) < 0.03),
            "emoji_usage_match": bool(abs(f1[26] - f2[26]) < 0.02),
            "typo_rate_match": bool(abs(f1[27] - f2[27]) < 0.03),
            "vocabulary_richness_match": bool(abs(f1[5] - f2[5]) < 0.05),  # type-token ratio
        }

        threshold = self.dec_threshold if domain_weight > 0.5 else self.pan_threshold
        is_match = bool(final_prob >= threshold)

        return {
            "same_author_probability": round(final_prob * 100, 2),
            "is_likely_match": is_match,
            "threshold_used": round(threshold, 3),
            "domain_routing": {
                "decypher_weight": round(domain_weight, 3),
                "pan_weight": round(1 - domain_weight, 3),
                "pan_model_probability": round(pan_prob * 100, 2),
                "decypher_model_probability": round(dec_prob * 100, 2),
            },
            "signals": signals,
        }

    def compare_handles(self, handle_id_a, handle_id_b, posts_df):
        """
        Compare two handles by concatenating all their posts and scoring.

        posts_df: a pandas DataFrame with at least ['handle_id', 'text'] columns
                  (i.e. load posts.csv once and pass it in — don't reload per call).
        """
        text_a = " ".join(posts_df.loc[posts_df["handle_id"] == handle_id_a, "text"].astype(str))
        text_b = " ".join(posts_df.loc[posts_df["handle_id"] == handle_id_b, "text"].astype(str))

        if not text_a or not text_b:
            raise ValueError(f"No posts found for handle_id(s): "
                              f"{handle_id_a if not text_a else ''} {handle_id_b if not text_b else ''}".strip())

        result = self.compare_texts(text_a, text_b)
        result["handle_a"] = handle_id_a
        result["handle_b"] = handle_id_b
        return result

    def check_contradiction(self, handle_id_a, handle_id_b, handles_df):
        """
        De-confliction check: do these two handles have overlapping active windows
        on DIFFERENT marketplaces at the same time? That weakens a same-actor claim.
        Expects handles_df with ['handle_id','marketplace','created_date','last_active_date'].
        """
        row_a = handles_df.loc[handles_df["handle_id"] == handle_id_a].iloc[0]
        row_b = handles_df.loc[handles_df["handle_id"] == handle_id_b].iloc[0]

        start_a, end_a = pd.to_datetime(row_a["created_date"]), pd.to_datetime(row_a["last_active_date"])
        start_b, end_b = pd.to_datetime(row_b["created_date"]), pd.to_datetime(row_b["last_active_date"])

        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)
        has_overlap = overlap_start <= overlap_end
        different_marketplace = row_a["marketplace"] != row_b["marketplace"]

        contradiction = bool(has_overlap and different_marketplace)
        return {
            "contradiction_flag": contradiction,
            "overlap_days": max((overlap_end - overlap_start).days, 0) if has_overlap else 0,
            "note": ("Active on two different marketplaces during an overlapping window — "
                     "weakens same-actor confidence.") if contradiction else "No conflicting activity window found.",
        }


# ============================================================
# EXAMPLE USAGE (for the Backend Lead)
# ============================================================
if __name__ == "__main__":
    engine = DeCypherAuthorshipEngine(model_dir=".")

    posts = pd.read_csv("posts.csv")
    handles = pd.read_csv("handles.csv")

    # pick two handles belonging to the same ground-truth actor, for a sanity check
    gt = pd.read_csv("handles.csv")
    same_actor_handles = gt.groupby("actor_id_ground_truth")["handle_id"].apply(list)
    example_pair = next(h for h in same_actor_handles if len(h) >= 2)

    result = engine.compare_handles(example_pair[0], example_pair[1], posts)
    print(result)

    contradiction = engine.check_contradiction(example_pair[0], example_pair[1], handles)
    print(contradiction)
