import unittest
from html.parser import HTMLParser

from solution_tools import highlight_cpp, prepare_solution, tokenize


class SolutionToolsTests(unittest.TestCase):
    def test_standard_header_is_preserved_verbatim(self):
        header = ('#include <bits/stdc++.h>\nusing namespace std;\nusing ll = long long;\n'
                  '#ifdef LOCAL\n#include "algo/debug.h"\n#else\n'
                  '#define dbg(...) 0\n#define dbgn(...) 0\n#endif\n\n')
        result = prepare_solution(header + 'int32_t main() { dbg(42); return 0; }\n// solve time: 5 minutes\n// My idea.\n')
        self.assertTrue(result['source'].startswith(header))
        self.assertNotIn('dbg(42)', result['source'])
        self.assertEqual(result['analysis'], 'My idea.')
        self.assertEqual(result['solve_time'], '5 minutes')

    def test_comment_lines_disappear_but_original_spacing_remains(self):
        source = ('int a;\n'
                  '  // a note\n'
                  'int b; // inline note\n'
                  '\n'
                  '/* multiline\n'
                  '\n'
                  ' * note\n'
                  ' */\n'
                  'int c;\n'
                  '\n\n'
                  'int d;\n')
        self.assertEqual(prepare_solution(source)['source'], 'int a;\nint b;\n\nint c;\n\n\nint d;\n')

    def test_highlighting_escapes_html_and_preserves_code(self):
        source = '#include <iostream>\nint main() { return 42; }\nconst char* s = "<script> // test";\n'
        html = highlight_cpp(source)
        self.assertIn('class="cpp-keyword">int</span>', html)
        self.assertIn('class="cpp-number">42</span>', html)
        self.assertIn('class="cpp-directive">include</span>', html)
        self.assertIn('class="cpp-string">', html)
        self.assertNotIn('<script>', html)
        class Text(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data): self.text.append(data)
        parser = Text()
        parser.feed(html)
        self.assertEqual(''.join(parser.text), source)

    def test_multiline_raw_string_keeps_blank_lines_and_spaces(self):
        literal = 'R"tag(first  \n\n\n// inside string  \nlast)tag"'
        source = f'const char* s = {literal};\n// outside comment\nint x;\n'
        cleaned = prepare_solution(source)['source']
        self.assertIn(literal, cleaned)
        self.assertIn('last)tag";\nint x;', cleaned)

    def test_notes_and_timing_after_main(self):
        result = prepare_solution('''// private header
int32_t main() { if (true) { return 0; } }
// solve time: 15 minutes
// implementation time 33 minutes
//
// We use a Fenwick tree.

// The invariant is x < y.
''')
        self.assertEqual(result['solve_time'], '15 minutes')
        self.assertEqual(result['implementation_time'], '33 minutes')
        self.assertIn('We use a Fenwick tree.', result['analysis'])
        self.assertIn('\n\nThe invariant', result['analysis'])
        self.assertNotIn('private header', result['analysis'])
        self.assertNotIn('solve time', result['analysis'])
        self.assertNotIn('Fenwick', result['source'])

    def test_block_notes_and_alternate_timing(self):
        result = prepare_solution('''int32_t main() { return 0; }
/*
 * 18 mins to think (read editorial)
 * 15 minutes to implement
 *
 * Binary search + a priority queue.
 */
int helper() { return 1; } // not analysis
''')
        self.assertEqual(result['solve_time'], '18 mins (read editorial)')
        self.assertEqual(result['implementation_time'], '15 minutes')
        self.assertEqual(result['analysis'], 'Binary search + a priority queue.')
        self.assertIn('int helper()', result['source'])

    def test_literals_nested_calls_and_macro(self):
        source = r'''#define dbg(...) something(__VA_ARGS__)
#define dbgn(...) \
    something(__VA_ARGS__)
const char* url = "https://example.com/*keep*/";
const char* raw = R"tag( // dbg(x); /* literal */ )tag";
char c = '\'';
int n = 1'000;
int/* separate tokens */value = 1;
int32_t main() {
  dbg(pair(1, f(2)), "literal )", dbg(n));
  if (n) dbg(n); else value++;
  value += (dbg(n), 1);
  dbgn(n);
  return 0; // private comment
}
'''
        result = prepare_solution(source)
        self.assertIn('https://example.com/*keep*/', result['source'])
        self.assertIn('R"tag( // dbg(x); /* literal */ )tag"', result['source'])
        self.assertIn("1'000", result['source'])
        self.assertRegex(result['source'], r'int\s+value')
        self.assertIn('if (n) {} else value++;', result['source'])
        self.assertIn('((void)0)', result['source'])
        tokens = tokenize(result['source'])
        self.assertFalse(any(t.kind == 'comment' for t in tokens))
        self.assertFalse(any(t.kind == 'identifier' and t.text in ('dbg', 'dbgn') for t in tokens))
        self.assertEqual(result['analysis'], '')

    def test_debug_statements_remove_semicolons_and_newly_empty_lines(self):
        source = '''void solve() {
    ans += dp[x];
    dbg(x, dp, subt); // debugging
    self(x, u, self); // keep this call
    dbg(
        x, nested(1, 2)
    );
    dbg(x); dbgn(x);
    int a = 1; dbg(a); int b = 2; // keep both declarations
    ; // intentionally empty statement
}
'''
        self.assertEqual(prepare_solution(source)['source'], '''void solve() {
    ans += dp[x];
    self(x, u, self);
    int a = 1;  int b = 2;
    ;
}
''')

    def test_control_bodies_and_debug_expressions_stay_valid(self):
        source = '''void solve() {
    if (x) dbg(x); else use(x);
    if (x)
        dbg(x);
    else use(x);
    while (x) dbg(x);
    do dbg(x); while (x);
    for (; dbg(x); step()) use(x);
    return dbg(x);
}
'''
        cleaned = prepare_solution(source)['source']
        self.assertIn('if (x) {} else use(x);', cleaned)
        self.assertIn('if (x)\n        {}\n    else use(x);', cleaned)
        self.assertIn('while (x) {}', cleaned)
        self.assertIn('do {} while (x);', cleaned)
        self.assertIn('for (; ((void)0); step()) use(x);', cleaned)
        self.assertIn('return ((void)0);', cleaned)

    def test_comment_at_start_of_main_and_missing_metadata(self):
        result = prepare_solution('int32_t main() {\n// My idea.\nreturn 0;\n}')
        self.assertEqual(result['analysis'], 'My idea.')
        self.assertNotIn('solve_time', result)

    def test_no_main_does_not_extract_arbitrary_comments(self):
        result = prepare_solution('// solve time: 10 minutes\nvoid solve() { /* private */ }')
        self.assertEqual(result['analysis'], '')
        self.assertNotIn('solve_time', result)


if __name__ == '__main__':
    unittest.main()
