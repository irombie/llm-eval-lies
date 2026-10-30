"""Tests for the eval harness itself. An eval you cannot trust is worse than none.

Run: python -m pytest
"""

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import eval as ev  # noqa: E402
import judge_flip as jf  # noqa: E402

GOLD = {"category": "billing", "priority": "high"}


@pytest.mark.parametrize("raw, expected", [
    ('{"category": "billing", "priority": "high"}', GOLD),
    ('```json\n{"category": "billing", "priority": "high"}\n```', GOLD),
    ('Sure! {"category": "billing", "priority": "high"} Hope that helps.', GOLD),
    ("Sure! Here is the category: billing", None),
    ('{"category": "billing", "priority": }', None),
    ("[1, 2, 3]", None),
])
def test_parse(raw, expected):
    assert ev.parse(raw) == expected


@pytest.mark.parametrize("pred, expected", [
    (None, (0, "invalid_json")),
    ({"category": "sales", "priority": "high"}, (0, "off_schema")),
    ({"category": "billing", "priority": "urgent"}, (0, "off_schema")),
    ({"category": "billing"}, (0, "off_schema")),
    ({"category": "technical", "priority": "high"}, (0, "wrong")),
    ({"category": "billing", "priority": "low"}, (0, "wrong")),
    (GOLD, (1, "correct")),
])
def test_score_one(pred, expected):
    assert ev.score_one(pred, GOLD) == expected


def test_dataset_labels_are_in_schema():
    rows = ev.load_dataset(ROOT / "dataset.jsonl")
    assert len(rows) == 15
    for row in rows:
        assert row["message"].strip()


def test_bad_gold_label_fails_loudly(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"message": "hi", "label": {"category": "Billing", "priority": "high"}}) + "\n")
    with pytest.raises(ValueError, match="outside the schema"):
        ev.load_dataset(bad)


def test_seeded_mock_reproduces_the_noise_slide():
    random.seed(1772)
    data = ev.load_dataset(ROOT / "dataset.jsonl")
    scores = [round(ev.run_once(data, mock=True)[0] * len(data)) for _ in range(5)]
    assert scores == [13, 11, 11, 14, 12]  # 86.7%, 73.3%, 73.3%, 93.3%, 80.0%


def test_gate_exit_codes(capsys):
    assert ev.main(["--mock", "--seed", "0"]) == 0
    assert ev.main(["--mock", "--seed", "1"]) == 1


@pytest.mark.parametrize("raw, expected", [
    ("A", "A"), ("b", "B"), (" B.", "B"),
    ("Both are good, but I lean toward the first.", None),
])
def test_parse_verdict(raw, expected):
    assert jf.parse_verdict(raw) == expected
