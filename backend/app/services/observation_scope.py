"""Shared actor -> observation target resolution.

Observations can be keyed by an actor ID, primary/associated handle, or the
URL/name of an explicitly linked scan target. Keeping this resolution in one
place prevents the actor, correlation, graph, and export APIs from drifting.
"""

from typing import Iterable, Set


def build_observation_target_keys(
    actor_id: str,
    primary_handle: str,
    handles: Iterable[object] = (),
    scan_targets: Iterable[object] = (),
) -> Set[str]:
    keys: Set[str] = set()

    for value in (actor_id, primary_handle):
        if value:
            keys.add(str(value).strip().lower())

    for handle in handles:
        value = getattr(handle, "handle", None)
        if value:
            keys.add(str(value).strip().lower())

    for target in scan_targets:
        for attr in ("target_url", "name"):
            value = getattr(target, attr, None)
            if value:
                keys.add(str(value).strip().lower())

    return keys
