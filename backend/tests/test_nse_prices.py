"""3i data loader: corporate-action text parsing and the backward adjustment."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research"))

import nse_prices as npx  # noqa: E402


@pytest.mark.parametrize("purpose,fv,expected", [
    ("Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share", 5, [("split", 2.5)]),
    ("Face Value Split Rs.10/- To Rs.2/-", 10, [("split", 5.0)]),
    ("Bonus 1:1", 10, [("bonus", 2.0)]),
    ("Bonus-1:1", 10, [("bonus", 2.0)]),
    ("Bonus 4:1", 1, [("bonus", 5.0)]),
    ("Bonus 1:2", 10, [("bonus", 1.5)]),
    ("Rights 1:4 @Prem Rs.480/-", 10, [("rights", (1.0, 4.0, 490.0))]),
    ("Demerger", 10, [("demerger", None)]),
    ("Interim Dividend Rs.25/- Per Share", 10, [("dividend", 25.0)]),
    ("Dividend - Rs 5.50 Per Share", 1, [("dividend", 5.5)]),
    ("Final Dividend - Rs 2 Per Share / Special Dividend - Rs 1 Per Share", 1, [("dividend", 3.0)]),
    ("Dividend-150%", 2, [("dividend", 3.0)]),
    ("Annual General Meeting", 10, []),
    ("Fv Splt Frm Rs 10 To Re 1", 1, [("split", 10.0)]),
    ("Fv Splt Frm Rs 10 To Rs 2", 2, [("split", 5.0)]),
    ("Fv Spl-Rs10tore1/Div-1.50", 1, [("split", 10.0), ("dividend", 1.5)]),
    ("Bon 1:1/Fv Spl Rs.5tors.2", 2, [("split", 2.5), ("bonus", 2.0)]),
    ("Fv Spl-Rs10tors5/Bon-2:1", 5, [("split", 2.0), ("bonus", 3.0)]),   # 2 new per 1 held
    ("Rights 87:38 @ Premium Of Rs 2.50 Per Share", 10, [("rights", (87.0, 38.0, 12.5))]),
    ("Special Dividend - Rs 500/- Per Share", 10, [("dividend", 500.0)]),
])
def test_parse_purpose(purpose, fv, expected):
    assert npx.parse_purpose(purpose, fv) == expected


def test_bonus_and_split_in_one_row():
    acts = npx.parse_purpose("Bonus 1:1 And Face Value Split From Rs 10 To Rs 1", 10)
    assert ("split", 10.0) in acts and ("bonus", 2.0) in acts


def test_sub_division_is_not_a_dividend():
    assert npx.parse_purpose("Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share", 5) == [("split", 2.5)]
