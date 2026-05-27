from __future__ import annotations

import asyncio
import math
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, Query, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from podcast_generator.config import Settings
from podcast_generator.models import ArticleSummary, GenerationJob, JobStatus
from podcast_generator.builder import PodcastGenerator
from podcast_generator.fetcher import get_article_list, fetch_article_html
from podcast_generator.web.db import init_db, add_episode, get_episodes
from podcast_generator.web.auth import verify_web_password, verify_api_token

templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)

_generation_jobs: dict[str, GenerationJob] = {}
_article_cache: dict[str, list[ArticleSummary] | str] = {"articles": [], "newsletter_url": ""}
_article_html_cache: dict[str, str] = {}
_cfg = Settings()


@asynccontextmanager
async def _lifespan(app):
    init_db()
    (_cfg.output_dir / "daily").mkdir(parents=True, exist_ok=True)
    (_cfg.output_dir / "weekly").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Podcast Generator API",
    description="Generate podcast episodes from newsletters",
    version="2.0.0",
    lifespan=_lifespan,
)


# ── Web UI Routes ──────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _=Depends(verify_web_password)):
    episodes = get_episodes()
    return templates.TemplateResponse(
        request, "index.html", {"episodes": episodes}
    )


@app.post("/fetch-articles", response_class=HTMLResponse)
async def fetch_articles(
    request: Request,
    newsletter_url: str = Form(...),
    _=Depends(verify_web_password),
):
    try:
        archive = (
            f"{newsletter_url}/archive"
            if newsletter_url
            else _cfg.archive_url
        )
        articles = await get_article_list(
            archive,
            load_more_selector=_cfg.load_more_selector,
            link_pattern=_cfg.link_pattern,
            max_articles=_cfg.max_articles,
        )
        _article_cache["articles"] = articles
        _article_cache["newsletter_url"] = newsletter_url
    except Exception as e:
        return HTMLResponse(
            content=(
                "<div class='text-red-500 bg-red-50 p-4 rounded-xl "
                "border border-red-200'>"
                f"Errore durante il recupero: {e}</div>"
            )
        )

    return await _render_articles(request, page=1)


async def _render_articles(
    request: Request,
    page: int = 1,
    per_page: int = 6,
    partial: bool = False,
):
    articles = _article_cache.get("articles", [])
    newsletter_url = _article_cache.get("newsletter_url", "")
    total = len(articles)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page

    return templates.TemplateResponse(
        request,
        "articles.html",
        {
            "articles": articles[start:end],
            "newsletter_url": newsletter_url,
            "page": page,
            "total": total,
            "per_page": per_page,
            "total_pages": total_pages,
            "partial": partial,
        },
    )


@app.get("/articles", response_class=HTMLResponse)
async def get_articles(
    request: Request,
    page: int = Query(1),
    _=Depends(verify_web_password),
):
    return await _render_articles(request, page=page, partial=True)


@ app.post("/article", response_class=HTMLResponse)
async def article_detail(
    request: Request,
    url: str = Form(...),
    title: str = Form(...),
    newsletter_url: str = Form(default=""),
    date: str = Form(default=""),
    duration: str = Form(default=""),
    description: str = Form(default=""),
    _=Depends(verify_web_password),
):
    if url not in _article_html_cache:
        try:
            _article_html_cache[url] = await fetch_article_html(url)
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "article_detail.html",
        {
            "url": url,
            "title": title,
            "date": date,
            "duration": duration,
            "description": description,
            "content_html": _article_html_cache.get(url, ""),
            "newsletter_url": newsletter_url,
        },
    )


def _lookup_titles(urls: list[str]) -> list[str]:
    """Look up article titles from the in-memory cache."""
    cache = _article_cache.get("articles", [])
    url_to_title = {a.href: a.text for a in cache if isinstance(a, ArticleSummary)}
    return [url_to_title.get(u, "") for u in urls]


async def _run_generation(job_id: str, article_urls: list[str]):
    try:
        gen = PodcastGenerator()
        titles = _lookup_titles(article_urls)
        episode = await gen.build_from_urls(article_urls, titles=titles)

        ep_id = add_episode(
            title=episode.title,
            url=episode.url,
            date=episode.date_str,
            audio_path=f"/download/{episode.audio_path.parent.name}/{episode.audio_path.name}",
            script_path=str(episode.script_path),
        )

        _generation_jobs[job_id] = GenerationJob(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            download_url=(
                f"/download/{episode.audio_path.parent.name}/"
                f"{episode.audio_path.name}"
            ),
            title=episode.title,
            filename=episode.audio_path.name,
        )
    except Exception as e:
        _generation_jobs[job_id] = GenerationJob(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    background_tasks: BackgroundTasks,
    request: Request,
    _=Depends(verify_web_password),
):
    # Try form data first (from checkbox form in articles.html)
    form = await request.form()
    article_urls: list[str] = form.getlist("article_urls")
    newsletter_url: str = form.get("newsletter_url", "")

    # Fall back to JSON body (from article detail hx-vals)
    if not article_urls:
        try:
            body = await request.json()
            article_urls = body.get("article_urls", [])
            newsletter_url = body.get("newsletter_url", "")
        except Exception:
            raise HTTPException(status_code=400, detail="article_urls is required")

    if not article_urls:
        raise HTTPException(status_code=400, detail="article_urls is required")

    job_id = str(uuid.uuid4())
    _generation_jobs[job_id] = GenerationJob(
        job_id=job_id, status=JobStatus.PROCESSING
    )
    background_tasks.add_task(_run_generation, job_id, article_urls)

    return HTMLResponse(
        content=f"""
        <div hx-get="/check-status/{job_id}" hx-trigger="every 2s"
             hx-swap="outerHTML"
             class="flex items-center gap-3 text-blue-600 font-semibold
                    bg-blue-50 p-4 rounded-xl">
            <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10"
                        stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z
                         m2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135
                         5.824 3 7.938l3-2.647z"/>
            </svg>
            Generazione in corso...
        </div>
        """
    )


@app.get("/check-status/{job_id}", response_class=HTMLResponse)
async def check_status(job_id: str, _=Depends(verify_web_password)):
    job = _generation_jobs.get(job_id)
    if not job:
        return "Stato sconosciuto"

    if job.status == JobStatus.PROCESSING:
        return f"""
        <div hx-get="/check-status/{job_id}" hx-trigger="every 2s"
             hx-swap="outerHTML"
             class="flex items-center gap-3 text-blue-600 font-semibold
                    bg-blue-50 p-4 rounded-xl">
            <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10"
                        stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z
                         m2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135
                         5.824 3 7.938l3-2.647z"/>
            </svg>
            Stiamo lavorando al tuo audio...
        </div>
        """

    if job.status == JobStatus.COMPLETED:
        return f"""
        <div class="bg-green-50 p-4 rounded-xl border border-green-200
                    flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3 text-green-700 font-bold">
                <svg class="w-6 h-6" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round"
                          stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                <span>Podcast Pronto: {job.title}</span>
            </div>
            <a href="{job.download_url}" download
               class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold
                      hover:bg-green-700 transition shadow-md">
                Scarica MP3
            </a>
        </div>
        """

    return (
        f"<div class='p-4 bg-red-50 text-red-700 rounded-xl "
        f"border border-red-200'>"
        f"Errore: {job.error or 'Errore generico'}</div>"
    )


@app.get("/download/{folder}/{filename:path}")
async def download_file(folder: str, filename: str):
    path = _cfg.output_dir / folder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    return FileResponse(
        path, filename=filename, media_type="audio/mpeg"
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
async def login(
    password: str = Form(...),
):
    if not _cfg.web_password:
        return RedirectResponse("/", status_code=303)
    import hmac

    if hmac.compare_digest(password, _cfg.web_password):
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            key="auth_token",
            value=password,
            httponly=True,
            max_age=86400 * 7,
            samesite="lax",
        )
        return resp
    raise HTTPException(status_code=401, detail="Password errata")


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("auth_token")
    return resp


# ── RSS Feed ───────────────────────────────────────────────────


@app.get("/rss")
async def rss_feed():
    episodes = get_episodes(limit=20)
    items = ""
    for ep in episodes:
        items += f"""
        <item>
            <title>{_xml_escape(ep['title'])}</title>
            <link>{ep['url']}</link>
            <guid>{ep['url'] or str(ep['id'])}</guid>
            <pubDate>{ep['date']}</pubDate>
            <enclosure url="{ep['audio_path']}" type="audio/mpeg"/>
        </item>
        """
    return HTMLResponse(
        content=f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Podcast Generator</title>
                <description>Podcast generati da newsletter</description>
                {items}
            </channel>
        </rss>
        """,
        media_type="application/xml",
    )


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ── REST API ───────────────────────────────────────────────────


@app.post("/api/v1/generate")
async def api_generate(
    request: Request,
    _=Depends(verify_api_token),
):
    body = await request.json()
    urls = body.get("urls", [])
    if not urls:
        raise HTTPException(status_code=400, detail="urls list is required")

    job_id = str(uuid.uuid4())
    _generation_jobs[job_id] = GenerationJob(
        job_id=job_id, status=JobStatus.PROCESSING
    )
    asyncio.create_task(_run_generation(job_id, urls))

    return {
        "job_id": job_id,
        "status": "processing",
        "status_url": f"/api/v1/status/{job_id}",
    }


@app.get("/api/v1/status/{job_id}")
async def api_status(
    job_id: str,
    _=Depends(verify_api_token),
):
    job = _generation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump(exclude_none=True)


@app.get("/api/v1/episodes")
async def api_episodes(
    limit: int = 20,
    _=Depends(verify_api_token),
):
    return get_episodes(limit=limit)


@app.get("/api/v1/episodes/{episode_id}")
async def api_episode(
    episode_id: int,
    _=Depends(verify_api_token),
):
    from podcast_generator.web.db import get_episode

    ep = get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep


@app.get("/api/v1/episodes/{episode_id}/audio")
async def api_download_audio(
    episode_id: int,
    _=Depends(verify_api_token),
):
    from podcast_generator.web.db import get_episode

    ep = get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    path = _cfg.output_dir / ep["audio_path"].lstrip("/")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(
        path, filename=path.name, media_type="audio/mpeg"
    )


@app.post("/api/v1/fetch-articles")
async def api_fetch_articles(
    request: Request,
    _=Depends(verify_api_token),
):
    body = await request.json()
    url = body.get("url", "")
    if not url:
        raise HTTPException(
            status_code=400, detail="url is required"
        )
    archive = f"{url}/archive"
    articles = await get_article_list(
        archive,
        load_more_selector=_cfg.load_more_selector,
        link_pattern=_cfg.link_pattern,
        max_articles=_cfg.max_articles,
    )
    return {"articles": [a.model_dump() for a in articles]}
