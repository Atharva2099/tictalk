"""Text processing utilities."""

import re


def strip_markdown_for_tts(text: str) -> str:
    """Remove markdown, tables, and LaTeX so TTS doesn't speak formatting."""
    # LaTeX: remove block math $$...$$ and inline $...$
    text = re.sub(r"\$\$[\s\S]*?\$\$", " ", text)
    text = re.sub(r"\$[^$]+\$", " ", text)
    # LaTeX commands -> readable
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1 over \2", text)
    text = re.sub(r"\\sqrt\{([^}]*)\}", r"square root of \1", text)
    text = re.sub(r"\\theta", "theta", text, flags=re.I)
    text = re.sub(r"\\alpha", "alpha", text, flags=re.I)
    text = re.sub(r"\\pi", "pi", text, flags=re.I)
    text = re.sub(r"\\cos", "cos", text, flags=re.I)
    text = re.sub(r"\\sin", "sin", text, flags=re.I)
    text = re.sub(r"\\tan", "tan", text, flags=re.I)
    text = re.sub(r"\\approx", "approximately", text, flags=re.I)
    text = re.sub(r"\\times", "times", text, flags=re.I)
    text = re.sub(r"\\left|\\right", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    # Tables: remove | and separator rows (|---|)
    lines = text.split("\n")
    result_lines = []
    for line in lines:
        if re.match(r"^[\s|:\-]+$", line):
            continue
        cell_text = " ".join(c.strip() for c in line.split("|") if c.strip())
        if cell_text:
            result_lines.append(cell_text)
    text = "\n".join(result_lines)
    # Bold, italic, code
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"[\*_`#|]+", " ", text)
    # Unicode math symbols
    text = text.replace("≈", " approximately ")
    text = text.replace("×", " times ")
    text = text.replace("√", " square root ")
    return " ".join(text.split())


def extract_sentences(buf: str) -> tuple[list[str], str]:
    """Extract complete sentences from buffer. Returns (sentences, remainder)."""
    result: list[str] = []
    remainder = buf
    while True:
        m = re.search(r".*?[.!?\n]", remainder, re.DOTALL)
        if not m:
            break
        s = m.group(0).strip()
        if s:
            result.append(s)
        remainder = remainder[m.end() :].lstrip()
    if len(remainder) >= 80:
        result.append(remainder.strip())
        remainder = ""
    return result, remainder
