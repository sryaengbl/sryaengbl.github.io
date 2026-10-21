# Blog

A small server-rendered blog using FastAPI, Jinja2, and Markdown. HTML and CSS only; no frontend build step.

## Run locally

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn blog.main:app --reload
```

Open http://127.0.0.1:8000.

## Write a post

Content lives directly under `blog/ml/`, `blog/competitive-programming/`, and `blog/research/`. Add UTF-8 Markdown at any depth in those sections and use a first-line `# Title` heading. The home page discovers posts automatically. For example, `blog/competitive-programming/algorithms/fenwick-trees.md` appears at `/posts/competitive-programming/algorithms/fenwick-trees`. Section overview pages use `index.md` and retain `/index` in their URL.

The `blog/competitive-programming/solutions/{codeforces,usaco,icpc}/` folders are available for Markdown writeups. C++ source stays in the separate `CompProgramming` project, alongside its input and output files.

## Solution source

`/solutions` recursively indexes only `.cpp` files inside the `codeforces`, `usaco`, and `icpc` folders of the sibling `CompProgramming` project. It displays escaped source code; it does not execute solutions or expose `.in` and `.out` files. Root-level scratch files and other folders are excluded.

The default source directory is `C:\Users\Brandon\Projects\CompProgramming` for this checkout. Override it before starting the server when needed:

```powershell
$env:COMP_PROGRAMMING_DIR = 'C:\Users\Brandon\Projects\CompProgramming'
```

The source directory must also be available on the deployment host. Missing platform directories display an empty list. New C++ files appear on the next page request.

The included posts are placeholders. Markdown files are trusted author content and may contain raw HTML; do not accept untrusted post uploads.

Deployment requires a Python server that can run `uvicorn blog.main:app --host 0.0.0.0 --port 8000`.
