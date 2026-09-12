"""A bar's value must not sit in its own axis's tick row (#52).

`percent_body_fat` is the only scored field whose value magnitude coincides with
its axis labels -- values run 10-35 against ticks 8..58 -- so a value printed on
the tick line reads as one more number in the run. The template used to lift it
there and paint a white halo over the collision. These assertions are computed
from the template's own CSS rather than matched against it, so reformatting the
rule is fine and moving the value back into the ticks is not.
"""

import re
from pathlib import Path

import pytest

_TEMPLATES = Path("src/inform/synthetic/templates")
# Chrome's default line box for a run of digits, as a multiple of font-size.
# Only used to turn font sizes into bands; the assertions have px of slack.
_LINE_HEIGHT = 1.2
# Both devices clear their tick line by 9.2px. 8.0 leaves room for a font or
# row-height tweak without a false failure, and is far enough above the ~4-6px
# that separates digits *inside* a number (#52) to mean something.
_MIN_GAP_PX = 8.0


def _rule(css: str, selector: str) -> dict[str, str]:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"{selector} not found"
    declarations = {}
    for part in match.group(1).split(";"):
        if ":" in part:
            name, _, value = part.partition(":")
            declarations[name.strip()] = value.strip()
    return declarations


def _px(value: str) -> float:
    return float(re.match(r"(-?[\d.]+)px", value.strip()).group(1))


def _bands(device: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """(tick band, value band) as top/bottom offsets within `.plot`."""
    css = (_TEMPLATES / f"{device}.html").read_text(encoding="utf-8")
    ticks, bar, value = _rule(css, ".ticks"), _rule(css, ".bar"), _rule(css, ".bar .bv")

    # `.ticks` is inset:0 in `.plot`, so its text starts at the plot's top.
    tick_band = (0.0, _px(ticks["font-size"]) * _LINE_HEIGHT)
    # `.bv` is positioned against `.bar`, which is positioned against `.plot`.
    value_top = _px(bar["top"]) + _px(value["top"])
    value_band = (value_top, value_top + _px(value["font-size"]) * _LINE_HEIGHT)
    return tick_band, value_band


@pytest.mark.parametrize("device", ["inbody_270", "inbody_570"])
def test_the_bar_value_sits_below_the_tick_labels(device):
    (_, tick_bottom), (value_top, _) = _bands(device)

    assert value_top >= tick_bottom + _MIN_GAP_PX, (
        f"{device}: the bar value starts {value_top:.1f}px into the plot, "
        f"but the tick labels run to {tick_bottom:.1f}px"
    )


@pytest.mark.parametrize("device", ["inbody_270", "inbody_570"])
def test_the_bar_value_stays_inside_its_row(device):
    css = (_TEMPLATES / f"{device}.html").read_text(encoding="utf-8")
    plot_height = _px(_rule(css, ".grow .plot")["height"])
    _, (_, value_bottom) = _bands(device)

    assert value_bottom <= plot_height


@pytest.mark.parametrize("device", ["inbody_270", "inbody_570"])
def test_the_value_is_not_masked_over_whatever_is_behind_it(device):
    # The white background and halo existed to punch a hole through the tick
    # label the value was printed on top of. Nothing is behind it now, and a
    # mask would mean the collision had come back.
    css = (_TEMPLATES / f"{device}.html").read_text(encoding="utf-8")
    value = _rule(css, ".bar .bv")

    assert "background" not in value
    assert "box-shadow" not in value
