from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from ledger.core.canonical import canonical_json

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.text(max_size=30),
)


def json_values(max_leaves: int = 10):
    return st.recursive(
        json_scalars,
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
        ),
        max_leaves=max_leaves,
    )


@given(st.dictionaries(st.text(min_size=1, max_size=10), json_values()))
def test_canonical_json_stable_across_dict_ordering(d: dict) -> None:
    shuffled = dict(reversed(list(d.items())))
    assert canonical_json(d) == canonical_json(shuffled)


@given(st.dictionaries(st.text(min_size=1, max_size=10), json_values()))
def test_canonical_json_round_trips_through_standard_json(d: dict) -> None:
    out = canonical_json(d)
    assert json.loads(out.decode("utf-8")) == d


def test_canonical_json_rejects_nan_and_infinity() -> None:
    import pytest

    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_json({"x": float("inf")})


def test_canonical_json_sorts_keys() -> None:
    assert canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
