"""The real app, driven through Streamlit's AppTest (no browser needed)."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def run(**numbers):
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    for label, value in numbers.items():
        [w for w in at.number_input if w.label.startswith(label)][0].set_value(value)
    if numbers:
        at.run()
    assert not at.exception, [x.value for x in at.exception]
    return at


def headline(at):
    return [m.value for m in at.markdown if m.value.startswith("### Recommendation")][0]


def metric(at, label):
    return [m.value for m in at.metric if m.label.startswith(label)][0]


def test_default_review_shows_the_conflict():
    at = run()
    assert "PILOT (objective not met)" in headline(at)
    assert metric(at, "Modeled net return") == "6.04%"
    assert any("2026-08" in m.value and "4.22%" in m.value for m in at.markdown)


def test_looser_loss_limit_reaches_the_objective():
    at = run(**{"Worst 12-month loss limit": -20.0})
    assert "objective not met" not in headline(at)
    assert metric(at, "Modeled net return") == "6.81%"


def test_lower_objective_is_met_by_the_same_mix():
    at = run(**{"Return objective": 6.0})
    assert "objective not met" not in headline(at)
    assert metric(at, "Modeled net return") == "6.04%"


def test_loss_limit_switched_off_does_not_crash():
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    [c for c in at.checkbox if c.label.startswith("Apply the worst")][0].uncheck()
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    assert "objective not met" not in headline(at)


def test_every_review_date_runs():
    at = AppTest.from_file(APP, default_timeout=300)
    at.run()
    box = [s for s in at.selectbox if s.label.startswith("Annual review date")][0]
    for opt in box.options:
        box.set_value(opt)
        at.run()
        assert not at.exception, (opt, [x.value for x in at.exception])
