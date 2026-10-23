import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import build


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in ('href', 'src'))


class BuildTests(unittest.TestCase):
    def test_folder_threshold_nested_groups_and_source_preserved(self):
        with tempfile.TemporaryDirectory(dir=build.ROOT) as temporary:
            root = Path(temporary)
            solutions = root / 'source'
            folder = solutions / 'usaco' / 'round'
            folder.mkdir(parents=True)
            original = b'int32_t main() { dbg(1); }\n// solve time: 12 minutes\n// implementation time: 8 minutes\n// My analysis.\n'
            for name in ('a', 'b', 'c'):
                (folder / f'{name}.cpp').write_bytes(original)
            output = root / 'site'
            group_page = output / 'solutions/folders/usaco/round/index.html'
            with patch.object(build, 'OUTPUT', output), contextlib.redirect_stdout(io.StringIO()):
                build.build(solutions)
                self.assertFalse(group_page.exists())
                (folder / 'd.cpp').write_bytes(original)
                build.build(solutions)
                self.assertTrue(group_page.exists())
                index = (output / 'solutions/index.html').read_text(encoding='utf-8')
                self.assertIn('(4 solutions)', index)
                self.assertNotIn('a.cpp', index)
                page = output / 'solutions/usaco/round/a.cpp/index.html'
                html = page.read_text(encoding='utf-8')
                self.assertIn('12 minutes', html)
                self.assertIn('8 minutes', html)
                self.assertIn('My analysis.', html)
                self.assertNotIn('dbg(1)', html)
                self.assertIn('folders/usaco/round/index.html', html)
                nested = folder / 'nested'
                nested.mkdir()
                for n in range(4): (nested / f'{n}.cpp').write_bytes(original)
                build.build(solutions)
                self.assertIn('(4 solutions)', group_page.read_text(encoding='utf-8'))
                nested_page = output / 'solutions/folders/usaco/round/nested/index.html'
                self.assertTrue(nested_page.exists())
                for source in solutions.rglob('*.cpp'):
                    self.assertEqual(source.read_bytes(), original)
                for source in nested.glob('*.cpp'): source.unlink()
                (folder / 'd.cpp').unlink()
                build.build(solutions)
                self.assertFalse(group_page.exists())
                self.assertFalse(nested_page.exists())

    def test_links_escaping_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=build.ROOT) as temporary:
            root = Path(temporary)
            solutions = root / 'source'
            folder = solutions / 'codeforces' / 'round 1'
            folder.mkdir(parents=True)
            source = folder / 'a.cpp'
            source.write_text('// private comment\nint main() { const char* s = "<script>unsafe</script>"; }', encoding='utf-8')
            stamp = datetime(2026, 10, 22, 2, tzinfo=timezone.utc).timestamp()
            os.utime(source, (stamp, stamp))
            (folder / 'a.in').write_text('private input', encoding='utf-8')
            (solutions / 'scratch.cpp').write_text('scratch', encoding='utf-8')
            output = root / 'site'
            with patch.object(build, 'OUTPUT', output), contextlib.redirect_stdout(io.StringIO()):
                build.build(solutions)
                page = output / 'solutions/codeforces/round 1/a.cpp/index.html'
                self.assertIn('&lt;script&gt;', page.read_text(encoding='utf-8'))
                self.assertNotIn('private comment', page.read_text(encoding='utf-8'))
                self.assertIn('data-copy-code', page.read_text(encoding='utf-8'))
                self.assertIn('datetime="2026-10-21">10 / 21 / 26</time>', page.read_text(encoding='utf-8'))
                self.assertIn('datetime="2026-10-21">10 / 21 / 26</time>', (output / 'solutions/index.html').read_text(encoding='utf-8'))
                post_source = next(path for path in build.discover(build.CONTENT / 'ml', '*.md'))
                date = build.updated_date(post_source)
                post_page = output / 'posts' / post_source.relative_to(build.CONTENT).with_suffix('') / 'index.html'
                self.assertIn(f'datetime="{date["iso"]}">{date["label"]}</time>', post_page.read_text(encoding='utf-8'))
                self.assertTrue((output / 'static/copy.js').is_file())
                self.assertFalse(list(output.rglob('*.in')))
                self.assertFalse((output / 'solutions/scratch.cpp/index.html').exists())
                for html in output.rglob('*.html'):
                    parser = Links()
                    parser.feed(html.read_text(encoding='utf-8'))
                    for target in parser.targets:
                        url = urlsplit(target)
                        if url.scheme or url.netloc or not url.path:
                            continue
                        self.assertFalse(url.path.startswith('/'), (html, target))
                        self.assertTrue((html.parent / unquote(url.path)).is_file(), (html, target))
                homepage = (output / 'index.html').read_text(encoding='utf-8')
                self.assertNotIn('posts/competitive-programming/index/index.html', homepage)
                self.assertEqual(homepage.count('href="solutions/index.html"'), 1)
                keep = output / 'CNAME'
                keep.write_text('example.com', encoding='utf-8')
                source.unlink()
                build.build(solutions)
                self.assertFalse(page.exists())
                self.assertEqual(keep.read_text(encoding='utf-8'), 'example.com')
                snapshot = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
                build.build(solutions)
                self.assertEqual(snapshot, {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()})
                with self.assertRaises(ValueError):
                    build.build(root / 'missing')
                self.assertTrue((output / 'index.html').exists())


if __name__ == '__main__':
    unittest.main()
