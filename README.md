# Blog

A static HTML and CSS blog. Python builds Markdown and templates locally; the published site needs no Python server. A small optional script powers the code Copy button.

## Build and preview

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python build.py
```

Open `docs/index.html` directly, or preview with:

```powershell
python -m http.server 8000 --directory docs
```

Visit http://localhost:8000. Re-run the build after editing Markdown, templates, CSS, or C++ solutions. Edit source files rather than generated HTML in `docs/`. The build removes obsolete generated files using `docs/.generated-files` and preserves other files such as a custom `CNAME`.

## Content

Keep Markdown under `blog/ml/`, `blog/competitive-programming/`, and `blog/research/`, at any depth. Use a first-line `# Title`. The build discovers posts automatically. For example, `blog/ml/backpropagation.md` becomes `docs/posts/ml/backpropagation/index.html`.

Section `index.md` pages are generated but excluded from the homepage post list. The homepage links directly to algorithm articles and the solutions index. The platform folders in `blog/competitive-programming/solutions/` are available for Markdown writeups.

Site links in Markdown can use `/posts/ml/backpropagation` or `/solutions`; the builder converts these to relative HTML links. Templates and styles live in `blog/templates/` and `blog/static/`. Markdown is trusted author content and may include raw HTML.

## C++ solutions

The build recursively indexes `.cpp` files in the `codeforces`, `usaco`, and `icpc` folders of the sibling `CompProgramming` repository. Existing `.cpp`, `.in`, and `.out` files stay together and untouched. Only escaped C++ source is included in the website; programs are never executed. Scratch files outside those platform folders are excluded.

For this checkout the default source is `C:\Users\Brandon\Projects\CompProgramming`. Override it with:

```powershell
.venv\Scripts\python build.py --solutions-dir 'C:\path\to\CompProgramming'
```

`COMP_PROGRAMMING_DIR` also sets the default. The source directory is required only at build time. A missing source directory fails the build rather than replacing published solutions with empty lists.

Folders containing more than three C++ solutions (including nested solutions) get a separate index page. Smaller folders are listed directly, with their relative paths. Grouping is applied recursively, so contest folders such as `usaco/26-3` do not flood the main solutions list. Solution pages link back to their containing group.

The builder preserves the standard opening block from `#include <bits/stdc++.h>` through the `#ifdef LOCAL` debug includes, macro definitions, and closing `#endif` exactly as written. Outside that block, it removes comments and `dbg(...)` / `dbgn(...)` calls and their macro definitions from the displayed code. String and character literals, including raw strings, are preserved. An empty statement or void expression may remain where needed to preserve surrounding C++ syntax. Original files are only read and are never rewritten.

Lines occupied only by removed comments disappear; intentional blank lines remain. C++ highlighting is generated as HTML spans during the build, using muted colors for keywords, strings, numbers, and preprocessor directives in both light and dark mode. No JavaScript or additional dependencies are needed.

Write analysis as consecutive `//` comments or a `/* ... */` block immediately after the closing brace of `main()`. Blank lines between comments are allowed. Notes at the start of the function body are also supported. For example:

```cpp
int32_t main() {
    // program code
}

// solve time: 15 minutes
// implementation time: 33 minutes
//
// The main idea is to maintain prefix sums with a Fenwick tree.
// Each update and query takes O(log n).
```

Timing is displayed beside the solution; the remaining analysis appears above the cleaned code with its line breaks preserved. Missing timings are omitted. The parser also accepts `solution time 15 minutes`, `18 mins to think`, and `15 minutes to implement`. Notes end at the next non-comment code. All extraction and cleanup happens automatically when running `build.py`.

## GitHub Pages

Commit the generated `docs/` directory along with the sources. In repository Settings → Pages, choose **Deploy from a branch**, select your publishing branch, and choose **/docs**. The generated `.nojekyll` file tells Pages to serve the files directly. No Python runtime or build action is required on GitHub.
