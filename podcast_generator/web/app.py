from __future__ import annotations

import asyncio
import hmac
import math
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from podcast_generator.config import Settings
from podcast_generator.models import ArticleSummary, GenerationJob, JobStatus
from podcast_generator.builder import PodcastGenerator
from podcast_generator.fetcher import (
    get_article_list, fetch_article_html, get_rss_articles,
    get_email_articles, fetch_email_content, list_imap_folders,
)
from podcast_generator.web.db import init_db, add_episode, get_episodes, get_user_by_email, create_user
from podcast_generator.web.auth import (
    verify_api_token, get_current_user,
    init_oauth, create_session_token, _oauth,
)

templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)

_generation_jobs: dict[str, GenerationJob] = {}
_article_cache: dict = {
    "articles": [], "newsletter_url": "",
    "email_total": 0, "email_offset": 0, "email_limit": 100,
}
_article_html_cache: dict[str, str] = {}
_article_original_urls: dict[str, str] = {}
_cfg = Settings()


@asynccontextmanager
async def _lifespan(app):
    init_db()
    (_cfg.output_dir / "daily").mkdir(parents=True, exist_ok=True)
    (_cfg.output_dir / "weekly").mkdir(parents=True, exist_ok=True)
    init_oauth(_cfg)
    yield


app = FastAPI(
    title="Podcast Generator API",
    description="Generate podcast episodes from newsletters",
    version="2.0.0",
    lifespan=_lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=_cfg.jwt_secret,
    max_age=3600,  # OAuth state expires in 1 hour
    same_site="lax",
)


# ── Auth Routes ────────────────────────────────────────────────


def _callback_url(request: Request, provider: str) -> str:
    base = str(request.base_url).rstrip("/")
    return base.replace("127.0.0.1", "localhost") + f"/auth/callback?provider={provider}"


@app.get("/auth/google")
async def auth_google(request: Request):
    if not _cfg.oauth_google_client_id:
        return RedirectResponse("/login?error=google_not_configured", status_code=303)
    redirect_uri = _callback_url(request, "google")
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/github")
async def auth_github(request: Request):
    if not _cfg.oauth_github_client_id:
        return RedirectResponse("/login?error=github_not_configured", status_code=303)
    redirect_uri = _callback_url(request, "github")
    return await _oauth.github.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request, provider: str = Query("")):
    if not provider:
        return RedirectResponse("/login?error=no_provider", status_code=303)

    try:
        if provider == "google":
            token = await _oauth.google.authorize_access_token(request)
            userinfo = token.get("userinfo") or (
                await _oauth.google.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo", token=token
                )
            ).json()
            user_id = str(userinfo.get("sub", ""))
            email = userinfo.get("email", "")
            name = userinfo.get("name", "")
            picture = userinfo.get("picture", "")
        elif provider == "github":
            token = await _oauth.github.authorize_access_token(request)
            resp = await _oauth.github.get("https://api.github.com/user", token=token)
            userinfo = resp.json()
            if not userinfo.get("email"):
                emails_resp = await _oauth.github.get(
                    "https://api.github.com/user/emails", token=token
                )
                for e in emails_resp.json():
                    if e.get("primary"):
                        userinfo["email"] = e["email"]
                        break
            user_id = str(userinfo.get("id", ""))
            email = userinfo.get("email", "")
            name = userinfo.get("name", "") or userinfo.get("login", email.split("@")[0])
            picture = userinfo.get("avatar_url", "")
        else:
            return RedirectResponse(f"/login?error=unknown_provider:{provider}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/login?error={provider}_auth_failed:{e}", status_code=303)

    if not email:
        return RedirectResponse("/login?error=no_email", status_code=303)

    user = get_user_by_email(email)
    if not user:
        user = create_user(email, name, picture, provider, user_id)

    session_token = create_session_token(user, _cfg.jwt_secret)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax",
    )
    return resp


# ── Web UI Routes ──────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: dict = Depends(get_current_user)):
    episodes = get_episodes()
    return templates.TemplateResponse(
        request, "index.html", {"episodes": episodes, "config": _cfg, "user": user}
    )


@app.post("/imap-folders", response_class=JSONResponse)
async def imap_folders(_=Depends(get_current_user)):
    if not _cfg.imap_host or not _cfg.imap_user or not _cfg.imap_password:
        return JSONResponse(
            {"error": "Configura prima Host, Email e Password nelle impostazioni"},
            status_code=400,
        )
    try:
        folders = await list_imap_folders(
            _cfg.imap_host, _cfg.imap_user, _cfg.imap_password
        )
        return {"folders": folders}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/imap-debug", response_class=JSONResponse)
async def imap_debug(_=Depends(get_current_user)):
    if not _cfg.imap_host or not _cfg.imap_user or not _cfg.imap_password:
        return JSONResponse({"error": "Configura prima le credenziali"}, status_code=400)
    try:
        from imap_tools import MailBox
        import imaplib

        results = {}
        with MailBox(_cfg.imap_host).login(_cfg.imap_user, _cfg.imap_password) as mb:
            # Test 1: count total and sample labels in All Mail using search()
            mb.folder.set("[Gmail]/Tutti i messaggi")
            _, data = mb.client.search(None, "ALL")
            seqs = (data[0] or b"").split()
            results["total_all_mail"] = len(seqs)

            # Fetch X-GM-LABELS for last 3 messages (checking format)
            sample_labels = {}
            for seq in seqs[-3:]:
                try:
                    typ, ld = mb.client.fetch(seq, "(X-GM-LABELS UID)")
                    sample_labels[seq.decode()] = str(ld)
                except Exception as e:
                    sample_labels[seq.decode()] = f"error: {e}"
            results["sample_labels"] = sample_labels

            # Test 2: search with X-GM-LABELS using regular search()
            for label in ["Forum", "CATEGORY_FORUM", "Categoria/Forum", "^FORUM"]:
                try:
                    _, data = mb.client.search(None, "X-GM-LABELS", label)
                    results[f"labels_{label}"] = len((data[0] or b"").split())
                except Exception as e:
                    results[f"labels_{label}"] = f"error: {e}"

            # Test 3: messages in Speciali folder
            try:
                mb.folder.set("[Gmail]/Speciali")
                _, data = mb.client.search(None, "ALL")
                results["speciali_count"] = len((data[0] or b"").split())
                # Fetch labels of last message in Speciali
                seqs = (data[0] or b"").split()
                if seqs:
                    typ, ld = mb.client.fetch(seqs[-1], "(X-GM-LABELS)")
                    results["speciali_labels"] = str(ld)
            except Exception as e:
                results["speciali_count"] = f"error: {e}"

            # Test 4: verify current folder name
            results["current_folder"] = mb.folder.get()

        return results
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/fetch-articles", response_class=HTMLResponse)
async def fetch_articles(
    request: Request,
    newsletter_url: Optional[str] = Form(None),
    source_type: str = Form("web"),
    _=Depends(get_current_user),
):
    try:
        if source_type == "email":
            articles, total = await get_email_articles(
                _cfg.imap_host, _cfg.imap_user, _cfg.imap_password,
                _cfg.imap_folder, limit=_cfg.imap_max_emails,
            )
            _article_cache["newsletter_url"] = _cfg.imap_folder or "Email Inbox"
            _article_cache["email_total"] = total
            _article_cache["email_offset"] = _cfg.imap_max_emails
            _article_cache["email_limit"] = _cfg.imap_max_emails
        elif newsletter_url and (newsletter_url.endswith(".xml") or "/feed" in newsletter_url or "rss" in newsletter_url):
            articles = await get_rss_articles(newsletter_url)
            _article_cache["newsletter_url"] = newsletter_url
            _article_cache["email_total"] = 0
        else:
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
            _article_cache["newsletter_url"] = newsletter_url or _cfg.newsletter_url
            _article_cache["email_total"] = 0

        _article_cache["articles"] = articles
    except Exception as e:
        return HTMLResponse(
            content=(
                "<div class='text-red-500 bg-red-50 p-4 rounded-xl "
                "border border-red-200'>"
                f"Errore durante il recupero: {e}</div>"
            )
        )

    return await _render_articles(request, page=1)


@app.post("/fetch-more-emails", response_class=HTMLResponse)
async def fetch_more_emails(
    request: Request,
    _=Depends(get_current_user),
):
    offset = _article_cache.get("email_offset", 100)
    limit = _article_cache.get("email_limit", 100)
    total = _article_cache.get("email_total", 0)

    if offset >= total:
        return HTMLResponse("")

    try:
        articles, _ = await get_email_articles(
            _cfg.imap_host, _cfg.imap_user, _cfg.imap_password,
            _cfg.imap_folder, offset=offset, limit=limit,
        )
        existing = _article_cache.get("articles", [])
        if isinstance(existing, list):
            _article_cache["articles"] = existing + articles
        _article_cache["email_offset"] = offset + limit

        return await _render_articles(request, page=1)
    except Exception as e:
        return HTMLResponse(
            f"<div class='text-red-500'>Errore: {e}</div>"
        )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse(
        request, "settings.html", {"config": _cfg, "user": user}
    )


@app.post("/save-settings")
async def save_settings(
    request: Request,
    ui_primary_color: str = Form(...),
    ui_accent_color: str = Form(...),
    imap_host: str = Form(...),
    imap_user: str = Form(...),
    imap_password: str = Form(...),
    imap_folder: str = Form(...),
    imap_max_emails: int = Form(100),
    language: str = Form("italiano"),
    _=Depends(get_current_user),
):
    _cfg.ui_primary_color = ui_primary_color
    _cfg.ui_accent_color = ui_accent_color
    _cfg.imap_host = imap_host
    _cfg.imap_user = imap_user
    _cfg.imap_password = imap_password
    _cfg.imap_folder = imap_folder
    _cfg.imap_max_emails = imap_max_emails
    _cfg.language = language

    # In a real app, we'd save to .env or a DB. For now, it's in-memory for the session.
    return RedirectResponse(url="/settings", status_code=303)


async def _render_articles(
    request: Request,
    page: int = 1,
    per_page: int = 6,
    partial: bool = False,
):
    articles = _article_cache.get("articles", [])
    newsletter_url = _article_cache.get("newsletter_url", "")
    email_total = _article_cache.get("email_total", 0)
    email_offset = _article_cache.get("email_offset", 0)
    total = email_total if email_total > len(articles) else len(articles)
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
            "config": _cfg,
            "email_total": email_total,
            "email_offset": email_offset,
        },
    )


@app.get("/articles", response_class=HTMLResponse)
async def get_articles(
    request: Request,
    page: int = Query(1),
    _=Depends(get_current_user),
):
    return await _render_articles(request, page=page, partial=False)


@ app.post("/article", response_class=HTMLResponse)
async def article_detail(
    request: Request,
    url: str = Form(...),
    title: str = Form(...),
    newsletter_url: str = Form(default=""),
    date: str = Form(default=""),
    duration: str = Form(default=""),
    description: str = Form(default=""),
    _=Depends(get_current_user),
):
    original_url = ""
    if url.startswith("email://"):
        uid = url[len("email://"):]
        try:
            newsletter = await fetch_email_content(
                _cfg.imap_host, _cfg.imap_user, _cfg.imap_password,
                uid, _cfg.imap_folder, raw_html=True,
            )
            _article_html_cache[url] = newsletter.content
            # Extract first meaningful link from email content
            for href in re.findall(r'href="(https?://[^"]+)"', newsletter.content):
                if not any(s in href for s in ("google.com/", "facebook.com/", "twitter.com/", "unsubscribe", "click=", "utm_", "track")):
                    original_url = href
                    break
            if not original_url:
                m = re.search(r"https?://[^\s<>\"']+", newsletter.content)
                if m:
                    original_url = m.group(0)
            title = newsletter.title or title
            date = str(newsletter.date) if newsletter.date else date
        except Exception:
            if url not in _article_html_cache:
                try:
                    _article_html_cache[url] = await fetch_article_html(url)
                except Exception:
                    pass
    else:
        if url not in _article_html_cache:
            try:
                _article_html_cache[url] = await fetch_article_html(url)
            except Exception:
                pass

    _article_original_urls[url] = original_url

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
            "original_url": original_url,
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
        gen = PodcastGenerator(config=_cfg)
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
    request: Request,
    _=Depends(get_current_user),
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
    asyncio.create_task(_run_generation(job_id, article_urls))

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
async def check_status(job_id: str, _=Depends(get_current_user)):
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
    has_oauth = bool(_cfg.oauth_google_client_id or _cfg.oauth_github_client_id)
    has_password = bool(_cfg.web_password)
    return templates.TemplateResponse(
        request, "login.html",
        {"config": _cfg, "has_oauth": has_oauth, "has_password": has_password},
    )


@app.post("/login")
async def login(
    request: Request,
    password: str = Form(...),
):
    from podcast_generator.web.auth import create_session_token

    if not _cfg.web_password:
        return RedirectResponse("/", status_code=303)

    if not hmac.compare_digest(password, _cfg.web_password):
        raise HTTPException(status_code=401, detail="Password errata")

    user = {"id": 0, "email": "admin@local", "name": "Admin", "picture": ""}
    session_token = create_session_token(user, _cfg.jwt_secret)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax",
    )
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
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
