"""The frog-in-the-pan tie-break (prereg-fip-tiebreak.md): the ID formula and
the order vacancies are filled in."""
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "research"))

import momentum_3i as m3  # noqa: E402
import momentum_fip as fip  # noqa: E402

N = 261   # rows 0..260: a start close and 260 daily returns


def _chain(closes):
    return {"idx": list(range(len(closes))), "close": closes}


def _smooth(up=True):
    return _chain([100 * (1.001 if up else 0.999) ** i for i in range(N)])


def _jump():
    return _chain([100.0] * (N - 1) + [130.0])


def test_id_is_minus_one_for_a_steady_winner_and_near_zero_for_one_jump():
    assert fip.information_discreteness(_smooth(), 0, N - 1) == -1
    assert abs(fip.information_discreteness(_jump(), 0, N - 1) + 1 / 260) < 1e-12


def test_id_takes_the_sign_of_the_formation_return():
    # a steady loser is as "continuous" as a steady winner
    assert fip.information_discreteness(_smooth(up=False), 0, N - 1) == -1


def test_no_id_without_200_returns_or_with_a_flat_formation_return():
    assert fip.information_discreteness(_chain([100 + i for i in range(150)]), 0, 149) is None
    assert fip.information_discreteness(_chain([100.0] * N), 0, N - 1) is None
    assert fip.information_discreteness(_smooth(), -5, N - 1) is None   # no close on or before the start


def test_vacancies_fill_by_lowest_id_inside_the_top_30_only():
    months = ["m%02d" % i for i in range(15)]
    me_idx = {m: 0 for m in months}
    me_idx[months[13]] = N - 1          # the month before the rebalance month
    order = ["n%02d" % i for i in range(32)]
    chains = {n: _jump() for n in order}
    chains["n29"] = _smooth()           # the most continuous name sits at rank 30
    chains["n31"] = _smooth()           # as continuous, but ranked 32: outside the cut
    chains["n00"] = _chain([100.0] * N)  # no ID
    got = fip.FipOrder()(order, chains, me_idx, months, months[14])
    assert got[0] == "n29"
    assert got[1:29] == order[1:29]     # ties keep their rank order
    assert got[29] == "n00"             # a name with no ID comes after those with one
    assert got[30:] == order[m3.RANK_KEEP:]
