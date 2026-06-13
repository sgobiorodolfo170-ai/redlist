from src.utils.color import darken_color, lighten_color


class TestLightenColor:
    def test_basic(self):
        assert lighten_color("#ff0000") == "#ff1414"

    def test_white_stays_white(self):
        assert lighten_color("#ffffff") == "#ffffff"

    def test_unknown_format_returns_as_is(self):
        assert lighten_color("rgb(255, 0, 0)") == "rgb(255, 0, 0)"


class TestDarkenColor:
    def test_basic(self):
        assert darken_color("#ff0000") == "#eb0000"

    def test_black_stays_black(self):
        assert darken_color("#000000") == "#000000"

    def test_unknown_format_returns_as_is(self):
        assert darken_color("rgb(0, 0, 0)") == "rgb(0, 0, 0)"
