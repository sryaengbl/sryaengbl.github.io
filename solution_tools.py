"""Prepare a read-only presentation copy of competitive programming solutions."""

import re
from html import escape
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int


# Strings are recognized before comments so URLs, escaped quotes, raw strings,
# and comment-like text inside literals survive the cleanup.
TOKEN = re.compile(
    r'(?P<literal>(?:u8|u|U|L)?R"(?P<delimiter>[^\s()\\]{0,16})\([\s\S]*?\)(?P=delimiter)"'
    r'|(?:u8|u|U|L)?"(?:\\[\s\S]|[^"\\])*"'
    r"|(?:u8|u|U|L)?'(?:\\[\s\S]|[^'\\\n])*')"
    r'|(?P<comment>//(?:\\\r?\n|[^\n])*|/\*[\s\S]*?(?:\*/|\Z))'
    r"|(?P<number>\b\d[\w.']*)"
    r'|(?P<space>\s+)'
    r'|(?P<identifier>[a-zA-Z_]\w*)'
    r'|(?P<symbol>.)', re.DOTALL,
)


def tokenize(source):
    # lastgroup is 'literal' even for raw strings with a named delimiter.
    return [Token(match.lastgroup, match[0], match.start(), match.end()) for match in TOKEN.finditer(source)]


CPP_KEYWORDS = set('''alignas alignof asm auto bool break case catch char char8_t char16_t char32_t
class concept const consteval constexpr constinit const_cast continue co_await co_return co_yield
decltype default delete do double dynamic_cast else enum explicit export extern false float for friend
goto if inline int long mutable namespace new noexcept nullptr operator private protected public
register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct
switch template this thread_local throw true try typedef typeid typename union unsigned using virtual
void volatile wchar_t while and and_eq bitand bitor compl not not_eq or or_eq xor xor_eq'''.split())


def highlight_cpp(source):
    """Return escaped HTML spans at build time; no browser script is required."""
    parts = []
    for token in tokenize(source):
        style = None
        if token.kind == 'literal': style = 'string'
        elif token.kind == 'number': style = 'number'
        elif token.kind == 'identifier' and token.text in CPP_KEYWORDS: style = 'keyword'
        elif token.kind == 'identifier':
            line_start = source.rfind('\n', 0, token.start) + 1
            if re.fullmatch(r'\s*#\s*', source[line_start:token.start]): style = 'directive'
        text = escape(token.text)
        parts.append(f'<span class="cpp-{style}">{text}</span>' if style else text)
    return ''.join(parts)


def token_lines(tokens, kind):
    """Identify lines occupied by a token kind, including multiline tokens."""
    lines, line = set(), 0
    for token in tokens:
        newlines = token.text.count('\n')
        if token.kind == kind:
            last = line + newlines - int(token.text.endswith('\n'))
            lines.update(range(line, last + 1))
        line += newlines
    return lines


def matching(tokens, start, opening, closing):
    depth = 0
    for i in range(start, len(tokens)):
        if tokens[i].kind == 'symbol':
            if tokens[i].text == opening: depth += 1
            if tokens[i].text == closing:
                depth -= 1
                if depth == 0: return i
    return None


def comment_text(text):
    if text.startswith('//'):
        return text[2:].removeprefix(' ')
    text = text[2:-2] if text.endswith('*/') else text[2:]
    return '\n'.join(re.sub(r'^\s*\* ?', '', line) for line in text.splitlines()).strip()


def main_notes(tokens):
    code = [token for token in tokens if token.kind not in ('space', 'comment')]
    for i, token in enumerate(code):
        if token.text != 'main' or i == 0 or code[i - 1].text not in ('int32_t', 'int', 'signed'):
            continue
        if i + 1 >= len(code) or code[i + 1].text != '(':
            continue
        end_args = matching(code, i + 1, '(', ')')
        if end_args is None or end_args + 1 >= len(code) or code[end_args + 1].text != '{':
            continue
        opening = code[end_args + 1]
        closing_index = matching(code, end_args + 1, '{', '}')
        if closing_index is None: continue
        closing = code[closing_index]
        # Prefer notes following main; also accept a comment at the top of main.
        for position in (closing.end, opening.end):
            selected = []
            for item in tokens:
                if item.start < position: continue
                if item.kind == 'space': continue
                if item.kind != 'comment': break
                selected.append(item)
            if selected:
                first, last = selected[0], selected[-1]
                text = ''.join(comment_text(t.text) if t.kind == 'comment' else t.text
                               for t in tokens if first.start <= t.start < last.end)
                return text.strip()
    return ''


def extract_timing(notes):
    timings, analysis = {}, []
    labels = {
        'solve_time': r'(?:solve(?:\s+time)?|solving\s+time|solution\s+time|time\s+to\s+solve|think(?:ing)?\s+time)',
        'implementation_time': r'(?:implementation(?:\s+time)?|implement(?:\s+time)?|coding\s+time|time\s+to\s+implement)',
    }
    for line in notes.splitlines():
        for key, label in labels.items():
            match = re.match(rf'^\s*{label}\s*[:=\-]?\s*(\d.*)$', line, re.I)
            if not match:
                action = r'(?:think|solve)' if key == 'solve_time' else r'(?:implement|code)'
                match = re.match(rf'^\s*(\d[^\n]*?\b(?:minutes?|mins?|hours?|hrs?|seconds?|secs?|[hms]))\s+to\s+{action}\b(.*)$', line, re.I)
                if match:
                    timings[key] = (match[1] + match[2]).strip()
                    break
            else:
                timings[key] = match[1].strip()
                break
        else:
            analysis.append(line)
    return timings, '\n'.join(analysis).strip()


def prepare_solution(source):
    # Preserve the author's standard opening block verbatim, including debug macros.
    header = ('#include <bits/stdc++.h>', 'using namespace std;', 'using ll = long long;',
              '#ifdef LOCAL', '#include "algo/debug.h"', '#else',
              '#define dbg(...) 0', '#define dbgn(...) 0', '#endif')
    lines = source.splitlines(keepends=True)
    preamble = ''
    if tuple(line.strip() for line in lines[:len(header)]) == header:
        end = len(header)
        while end < len(lines) and not lines[end].strip(): end += 1
        preamble = ''.join(lines[:end])
        source = ''.join(lines[end:])
    tokens = tokenize(source)
    notes = main_notes(tokens)
    timings, analysis = extract_timing(notes)
    # Replace comments with whitespace to avoid merging adjacent C++ tokens.
    cleaned = ''.join(re.sub(r'[^\r\n]', ' ', token.text) if token.kind == 'comment' else token.text for token in tokens)
    comment_lines = token_lines(tokens, 'comment')
    cleaned = ''.join(line for i, line in enumerate(cleaned.splitlines(keepends=True))
                      if i not in comment_lines or line.strip())
    code = [t for t in tokenize(cleaned) if t.kind != 'space']
    removals = []
    for i, token in enumerate(code):
        if token.kind != 'identifier' or token.text not in ('dbg', 'dbgn'):
            continue
        if i + 1 >= len(code) or code[i + 1].text != '(':
            continue
        # Debug macro definitions have no role in the displayed solution.
        line_start = cleaned.rfind('\n', 0, token.start) + 1
        if re.match(r'\s*#\s*define\s*$', cleaned[line_start:token.start]):
            end = cleaned.find('\n', token.end)
            while end >= 0 and cleaned[line_start:end].rstrip('\r').endswith('\\'):
                end = cleaned.find('\n', end + 1)
            removals.append((line_start, len(cleaned) if end < 0 else end))
            continue
        if i and code[i - 1].text in ('.', ':', '>'):
            continue
        end_call = matching(code, i + 1, '(', ')')
        if end_call is None:
            raise ValueError('Unbalanced debug call; cannot safely prepare blog copy.')
        end = code[end_call].end
        # Preserve the semicolon as an empty statement (e.g. if (x) dbg(x); else ...).
        # Expression-position calls use a neutral void expression instead.
        statement = end_call + 1 < len(code) and code[end_call + 1].text == ';'
        removals.append((token.start, end, '' if statement else '((void)0)'))
    # Apply outermost edits once; nested dbg(...) calls are removed with their parent.
    edits = []
    for removal in sorted(removals, key=lambda item: (item[0], -item[1])):
        start, end = removal[:2]
        if edits and start < edits[-1][1]: continue
        edits.append((start, end, removal[2] if len(removal) == 3 else ''))
    for start, end, replacement in reversed(edits):
        cleaned = cleaned[:start] + replacement + cleaned[end:]
    literal_lines = token_lines(tokenize(cleaned), 'literal')
    cleaned = '\n'.join(line if i in literal_lines else line.rstrip()
                        for i, line in enumerate(cleaned.splitlines())).strip() + '\n'
    return {'source': preamble + cleaned, 'analysis': analysis, **timings}
