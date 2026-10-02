from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "ai" / "nlp" / "evaluate_authorship.py"
SPEC = spec_from_file_location("decypher_evaluate_authorship", MODULE_PATH)
MODULE = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_pairs_is_balanced_and_uses_ground_truth_only():
    handles = pd.DataFrame(
        {
            "handle_id": ["H1", "H2", "H3", "H4", "H5"],
            "actor_id_ground_truth": ["A1", "A1", "A2", "A2", "A3"],
        }
    )

    pairs = MODULE.build_pairs(handles, max_positive=10, seed=26151)

    labels = [label for _, _, label in pairs]
    assert labels.count(1) == 2
    assert labels.count(0) == 2

    for left, right, label in pairs:
        if label == 1:
            left_actor = handles.loc[
                handles["handle_id"] == left, "actor_id_ground_truth"
            ].iloc[0]
            right_actor = handles.loc[
                handles["handle_id"] == right, "actor_id_ground_truth"
            ].iloc[0]
            assert left_actor == right_actor
        else:
            assert left != right


def test_aggregate_posts_groups_by_handle():
    posts = pd.DataFrame(
        {
            "handle_id": ["H1", "H1", "H2"],
            "text": ["alpha", "beta", "gamma"],
        }
    )

    result = MODULE.aggregate_posts(posts)

    assert result == {
        "H1": "alpha beta",
        "H2": "gamma",
    }
