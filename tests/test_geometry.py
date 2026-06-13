from unittest.mock import MagicMock

from src.utils.geometry import is_horizontal_overlap, is_vertical_overlap


def _make_rect(left, top, width, height):
    r = MagicMock()
    r.left.return_value = left
    r.right.return_value = left + width
    r.top.return_value = top
    r.bottom.return_value = top + height
    return r


class TestIsHorizontalOverlap:
    def test_overlapping(self):
        a = _make_rect(0, 0, 100, 50)
        b = _make_rect(50, 0, 100, 50)
        assert is_horizontal_overlap(a, b) is True

    def test_a_left_of_b_no_overlap(self):
        a = _make_rect(0, 0, 50, 50)
        b = _make_rect(100, 0, 50, 50)
        assert is_horizontal_overlap(a, b) is False

    def test_a_right_of_b_no_overlap(self):
        a = _make_rect(100, 0, 50, 50)
        b = _make_rect(0, 0, 50, 50)
        assert is_horizontal_overlap(a, b) is False

    def test_identical(self):
        a = _make_rect(10, 10, 100, 50)
        b = _make_rect(10, 10, 100, 50)
        assert is_horizontal_overlap(a, b) is True

    def test_touching_edges_considered_overlap(self):
        a = _make_rect(0, 0, 100, 50)
        b = _make_rect(100, 0, 50, 50)
        assert is_horizontal_overlap(a, b) is True


class TestIsVerticalOverlap:
    def test_overlapping(self):
        a = _make_rect(0, 0, 50, 100)
        b = _make_rect(0, 50, 50, 100)
        assert is_vertical_overlap(a, b) is True

    def test_a_above_b_no_overlap(self):
        a = _make_rect(0, 0, 50, 50)
        b = _make_rect(0, 100, 50, 50)
        assert is_vertical_overlap(a, b) is False

    def test_a_below_b_no_overlap(self):
        a = _make_rect(0, 100, 50, 50)
        b = _make_rect(0, 0, 50, 50)
        assert is_vertical_overlap(a, b) is False

    def test_identical(self):
        a = _make_rect(10, 10, 50, 100)
        b = _make_rect(10, 10, 50, 100)
        assert is_vertical_overlap(a, b) is True
