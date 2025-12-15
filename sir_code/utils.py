
def multiline_strip(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines())

def print_section(title: str, length: int = 80, c: str = '='):
    d, m = divmod(length - len(title) - 2, 2)
    print(f"{c * d}|{title}|{c * (d+m)}")