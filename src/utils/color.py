def lighten_color(color: str, amount: int = 20) -> str:
    if color.startswith("#"):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r, g, b = min(255, r + amount), min(255, g + amount), min(255, b + amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    return color


def darken_color(color: str, amount: int = 20) -> str:
    if color.startswith("#"):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        r, g, b = max(0, r - amount), max(0, g - amount), max(0, b - amount)
        return f"#{r:02x}{g:02x}{b:02x}"
    return color
