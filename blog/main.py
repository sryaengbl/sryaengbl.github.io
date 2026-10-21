import os
from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
CONTENT_SECTIONS = ("ml", "competitive-programming", "research")
PLATFORMS = ("codeforces", "usaco", "icpc")
SOLUTIONS_DIR = Path(os.environ.get("COMP_PROGRAMMING_DIR", str(BASE_DIR.parent.parent / "CompProgramming"))).resolve()


def section_label(section: str) -> str:
    return {"ml": "Machine learning", "competitive-programming": "Competitive programming", "research": "Research"}[section]


def content_paths():
    return sorted(path for section in CONTENT_SECTIONS for path in (BASE_DIR / section).rglob("*.md")
                  if path.resolve().is_relative_to((BASE_DIR / section).resolve()))


def solution_paths():
    return sorted(path for platform in PLATFORMS for path in (SOLUTIONS_DIR / platform).rglob("*.cpp")
                  if path.resolve().is_relative_to((SOLUTIONS_DIR / platform).resolve()))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def read_post(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    title = lines[0][2:] if lines and lines[0].startswith("# ") else path.stem.replace("-", " ").title()
    body = "\n".join(lines[1:]) if lines and lines[0].startswith("# ") else source
    return {
        "title": title,
        "category": path.relative_to(BASE_DIR).parts[0],
        "section_label": section_label(path.relative_to(BASE_DIR).parts[0]),
        "slug": path.relative_to(BASE_DIR).with_suffix("").as_posix(),
        # Post files are trusted, author-controlled Markdown, including raw HTML.
        "content": markdown.markdown(body, extensions=["fenced_code", "tables"]),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    posts = [read_post(path) for path in content_paths() if path.name != "index.md"]
    return templates.TemplateResponse(request=request, name="index.html", context={"posts": posts})


@app.get("/posts/{slug:path}", response_class=HTMLResponse, name="post")
def post(request: Request, slug: str):
    path = (BASE_DIR / f"{slug}.md").resolve()
    allowed = {p.resolve() for p in content_paths()}
    if path not in allowed:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(request=request, name="post.html", context={"post": read_post(path)})


@app.get("/solutions", response_class=HTMLResponse)
def solutions(request: Request):
    entries = [{"platform": p.relative_to(SOLUTIONS_DIR).parts[0],
                "slug": p.relative_to(SOLUTIONS_DIR).as_posix(),
                "title": p.relative_to(SOLUTIONS_DIR).as_posix()} for p in solution_paths()]
    return templates.TemplateResponse(request=request, name="solutions.html", context={"solutions": entries, "platforms": PLATFORMS})


@app.get("/solutions/{slug:path}", response_class=HTMLResponse, name="solution")
def solution(request: Request, slug: str):
    path = (SOLUTIONS_DIR / slug).resolve()
    if path not in {p.resolve() for p in solution_paths()}:
        raise HTTPException(status_code=404, detail="Solution not found")
    return templates.TemplateResponse(request=request, name="solution.html", context={
        "title": path.relative_to(SOLUTIONS_DIR).as_posix(),
        "source": path.read_text(encoding="utf-8", errors="replace"),
    })
