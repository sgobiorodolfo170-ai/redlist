from PyQt6.QtCore import QRect


def is_horizontal_overlap(geo1: QRect, geo2: QRect) -> bool:
    return not (geo1.right() < geo2.left() or geo1.left() > geo2.right())


def is_vertical_overlap(geo1: QRect, geo2: QRect) -> bool:
    return not (geo1.bottom() < geo2.top() or geo1.top() > geo2.bottom())
