"""Build static HTML into docs/: python build.py."""
import argparse
import os
import posixpath
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from solution_tools import highlight_cpp, prepare_solution

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'blog'
OUTPUT = ROOT / 'docs'
SECTIONS = {'ml': 'Machine learning', 'competitive-programming': 'Competitive programming', 'research': 'Research'}
PLATFORMS = ('codeforces', 'usaco', 'icpc')


def updated_date(path):
    date = datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo('America/Indiana/Indianapolis')).date()
    return {'iso': date.isoformat(), 'label': date.strftime('%m / %d / %y')}


def discover(root, pattern):
    return sorted(p for p in root.rglob(pattern) if p.is_file() and p.resolve().is_relative_to(root.resolve()))


def build(solutions_dir):
    solutions_dir = Path(solutions_dir).resolve()
    if not solutions_dir.is_dir():
        raise ValueError(f'Solution directory does not exist: {solutions_dir}. Use --solutions-dir.')
    env = Environment(loader=FileSystemLoader(CONTENT / 'templates'), autoescape=select_autoescape(),
                      trim_blocks=True, lstrip_blocks=True)
    files = {}

    def target(name, **values):
        if name == 'index': return 'index.html'
        if name == 'static': return 'static/' + values['path']
        if name == 'solutions': return 'solutions/index.html'
        if name == 'post': return 'posts/' + values['slug'] + '/index.html'
        if name == 'solution': return 'solutions/' + values['slug'] + '/index.html'
        if name == 'solution_folder': return 'solutions/folders/' + values['slug'] + '/index.html'
        raise ValueError(f'Unknown page: {name}')

    def relative(destination, page):
        return quote(posixpath.relpath(destination, posixpath.dirname(page) or '.'), safe='/.-_')

    def render(template, page, **context):
        context['url'] = lambda name, **values: relative(target(name, **values), page)
        files[page] = env.get_template(template).render(**context).encode('utf-8')

    posts = []
    for section, label in SECTIONS.items():
        for path in discover(CONTENT / section, '*.md'):
            lines = path.read_text(encoding='utf-8').splitlines()
            heading = bool(lines and lines[0].startswith('# '))
            slug = path.relative_to(CONTENT).with_suffix('').as_posix()
            page = target('post', slug=slug)
            body = '\n'.join(lines[1:] if heading else lines)
            # Translate root-relative site links in Markdown into portable HTML links.
            def rewrite(match):
                route, separator, fragment = match[1].partition('#')
                destination = route.lstrip('/').rstrip('/')
                destination = destination + '/index.html' if destination else 'index.html'
                return '](' + relative(destination, page) + ('#' + fragment if separator else '') + ')'
            body = re.sub(r'\]\((/(?:posts/|solutions(?:/|(?=[)#])))[^\s)]*)\)', rewrite, body)
            post = {'title': lines[0][2:] if heading else path.stem.replace('-', ' ').title(),
                    'category': section, 'section_label': label, 'slug': slug, 'updated': updated_date(path),
                    'content': markdown.markdown(body, extensions=['fenced_code', 'tables'])}
            render('post.html', page, post=post)
            if path.name != 'index.md': posts.append(post)

    solutions = []
    platform_entries = {}
    for platform in PLATFORMS:
        paths = discover(solutions_dir / platform, '*.cpp')
        folders = {}
        for path in paths:
            for parent in path.relative_to(solutions_dir).parents:
                if len(parent.parts) > 1:
                    folders.setdefault(parent.as_posix(), []).append(path)
        grouped = {folder for folder, members in folders.items() if len(members) > 3}

        def listing(prefix):
            entries, seen = [], set()
            for path in paths:
                relative_path = path.relative_to(solutions_dir)
                if not relative_path.is_relative_to(prefix): continue
                below = relative_path.relative_to(prefix)
                child = (Path(prefix) / below.parts[0]).as_posix()
                if len(below.parts) > 1 and child in grouped:
                    if child not in seen:
                        entries.append({'kind': 'solution_folder', 'slug': child,
                                        'title': below.parts[0], 'count': len(folders[child])})
                        seen.add(child)
                else:
                    entries.append({'kind': 'solution', 'slug': relative_path.as_posix(),
                                    'title': below.as_posix(), 'updated': updated_date(path)})
            return sorted(entries, key=lambda entry: (entry['kind'] != 'solution_folder', entry['title']))

        def back_link(slug):
            for parent in Path(slug).parents:
                if parent.as_posix() in grouped:
                    return {'kind': 'solution_folder', 'slug': parent.as_posix(), 'title': parent.name}
            return {'kind': 'solutions', 'slug': '', 'title': 'All solutions'}

        platform_entries[platform] = listing(platform)
        for folder in sorted(grouped):
            render('solution_folder.html', target('solution_folder', slug=folder),
                   title=folder, entries=listing(folder), back=back_link(folder))
        for path in paths:
            slug = path.relative_to(solutions_dir).as_posix()
            solutions.append({'platform': platform, 'slug': slug, 'title': slug})
            prepared = prepare_solution(path.read_text(encoding='utf-8', errors='replace'))
            render('solution.html', target('solution', slug=slug), title=slug,
                   back=back_link(slug), updated=updated_date(path), source_html=highlight_cpp(prepared['source']), **prepared)
    render('index.html', 'index.html', posts=posts)
    render('solutions.html', 'solutions/index.html', platform_entries=platform_entries, platforms=PLATFORMS)
    for path in discover(CONTENT / 'static', '*'):
        files['static/' + path.relative_to(CONTENT / 'static').as_posix()] = path.read_bytes()
    files['.nojekyll'] = b''

    # Only previously generated files inside docs/ are eligible for removal.
    manifest = OUTPUT / '.generated-files'
    previous = set(manifest.read_text(encoding='utf-8').splitlines()) if manifest.exists() else set()
    for name in previous | set(files):
        destination = (OUTPUT / name).resolve()
        if not destination.is_relative_to(OUTPUT.resolve()) or destination == OUTPUT.resolve():
            raise ValueError(f'Invalid output path: {name}')
    for name, content in files.items():
        destination = OUTPUT / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    for name in previous - set(files):
        (OUTPUT / name).unlink(missing_ok=True)
    manifest.write_text('\n'.join(sorted(files)) + '\n', encoding='utf-8')
    print(f'Built {len(posts)} posts and {len(solutions)} solutions into {OUTPUT}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solutions-dir', type=Path,
                        default=os.environ.get('COMP_PROGRAMMING_DIR', ROOT.parent / 'CompProgramming'))
    args = parser.parse_args()
    try:
        build(args.solutions_dir)
    except ValueError as error:
        parser.exit(1, f'Build failed: {error}\n')
