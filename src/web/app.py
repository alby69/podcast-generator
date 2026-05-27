import os
import asyncio
import uuid
from pathlib import Path
from typing import List
from datetime import datetime

from fastapi import FastAPI, Request, Form, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from playwright.async_api import async_playwright

from src.config import Config
from src.fetcher import get_article_list, fetch_content
from src.builder import build_daily, build_weekly, generate_script_daily, generate_script_weekly
from src.web.db import create_db_and_tables, get_session, EpisodeDB, engine

app = FastAPI(title="Podcast Generator Web")

# Assicurati che le directory di output esistano
cfg_default = Config()
(cfg_default.output_dir / "daily").mkdir(parents=True, exist_ok=True)
(cfg_default.output_dir / "weekly").mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory="src/web/templates")

generation_results = {}
MAX_RESULTS = 100

def check_auth(request: Request):
    password = os.getenv("WEB_PASSWORD")
    if not password:
        return True

    token = request.cookies.get("auth_token")
    if token == password:
        return True
    return False

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
async def login(password: str = Form(...)):
    expected = os.getenv("WEB_PASSWORD")
    if password == expected:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="auth_token", value=password, httponly=True)
        return response
    return HTMLResponse("Password errata", status_code=401)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends(get_session)):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    episodes = session.exec(select(EpisodeDB).order_by(EpisodeDB.created_at.desc())).all()
    return templates.TemplateResponse(request, "index.html", {"episodes": episodes})

@app.get("/rss")
async def rss_feed(request: Request, session: Session = Depends(get_session)):
    episodes = session.exec(select(EpisodeDB).order_by(EpisodeDB.created_at.desc())).all()

    base_url = str(request.base_url).rstrip("/")
    items_xml = ""
    for ep in episodes:
        items_xml += f"""
        <item>
            <title>{ep.title}</title>
            <link>{ep.url or base_url}</link>
            <description>Episodio generato il {ep.date}</description>
            <pubDate>{ep.created_at}</pubDate>
            <enclosure url="{base_url}{ep.audio_path}" length="0" type="audio/mpeg"/>
            <guid isPermaLink="false">{ep.id}</guid>
        </item>"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
        <channel>
            <title>Podcast Generator Feed</title>
            <link>{base_url}</link>
            <description>Il tuo feed personalizzato di newsletter tradotte</description>
            <language>it-it</language>
            {items_xml}
        </channel>
    </rss>"""
    return Response(content=rss_xml, media_type="application/xml")

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request, q: str = "", session: Session = Depends(get_session)):
    if not check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)

    statement = select(EpisodeDB).order_by(EpisodeDB.created_at.desc())
    if q:
        statement = statement.where(EpisodeDB.title.contains(q))

    episodes = session.exec(statement).all()
    return templates.TemplateResponse(request, "history_items.html", {"episodes": episodes})

@app.post("/fetch-articles", response_class=HTMLResponse)
async def fetch_articles(request: Request, newsletter_url: str = Form(...)):
    if not check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)
    cfg = Config(newsletter_url=newsletter_url)
    try:
        articles = await get_article_list(cfg.archive_url, cfg.load_more_selector, cfg.link_pattern)
    except Exception as e:
        return HTMLResponse(content=f"<div class='text-red-500 bg-red-50 p-4 rounded-xl border border-red-200'>Errore durante il recupero: {str(e)}</div>")

    return templates.TemplateResponse(request, "articles.html", {
        "articles": articles,
        "newsletter_url": newsletter_url
    })

async def run_generation_task(job_id: str, article_urls: List[str], newsletter_url: str):
    # Memory limit for generation_results
    if len(generation_results) > MAX_RESULTS:
        # Rimozione del risultato più vecchio
        oldest = next(iter(generation_results))
        del generation_results[oldest]

    cfg = Config(newsletter_url=newsletter_url)
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            newsletters = []
            for url in article_urls:
                link = {"href": url, "text": "Articolo"}
                nl = await fetch_content(context, link)
                newsletters.append(nl)
            await browser.close()

        if len(newsletters) == 1:
            episode = await build_daily(cfg, newsletters[0])
            folder = "daily"
            filename = episode.audio_path.name
        else:
            episode = await build_weekly(cfg, newsletters)
            folder = "weekly"
            filename = episode.audio_path.name

        # Persistenza nel DB
        with Session(engine) as session:
            new_ep = EpisodeDB(
                title=episode.title,
                url=episode.url or newsletter_url,
                date=episode.date_str,
                audio_path=f"/download/{folder}/{filename}",
                script_path=str(episode.script_path),
                created_at=datetime.now().isoformat()
            )
            session.add(new_ep)
            session.commit()
            session.refresh(new_ep)

        generation_results[job_id] = {
            "status": "completed",
            "download_url": f"/download/{folder}/{filename}",
            "filename": filename,
            "title": episode.title
        }
    except Exception as e:
        generation_results[job_id] = {"status": "error", "message": str(e)}

@app.post("/generate", response_class=HTMLResponse)
async def generate(
    background_tasks: BackgroundTasks,
    request: Request,
    article_urls: List[str] = Form(...),
    newsletter_url: str = Form(...)
):
    if not check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)
    job_id = str(uuid.uuid4())
    generation_results[job_id] = {"status": "processing"}
    background_tasks.add_task(run_generation_task, job_id, article_urls, newsletter_url)

    return HTMLResponse(content=f"""
        <div hx-get="/check-status/{job_id}" hx-trigger="every 2s" hx-swap="outerHTML" class="flex items-center gap-3 text-blue-600 font-semibold bg-blue-50 p-4 rounded-xl">
            <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generazione in corso...
        </div>
    """)

@app.get("/check-status/{job_id}", response_class=HTMLResponse)
async def check_status(job_id: str):
    result = generation_results.get(job_id)
    if not result:
        return "Stato sconosciuto"

    if result["status"] == "processing":
        return f"""
            <div hx-get="/check-status/{job_id}" hx-trigger="every 2s" hx-swap="outerHTML" class="flex items-center gap-3 text-blue-600 font-semibold bg-blue-50 p-4 rounded-xl">
                <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Stiamo lavorando al tuo audio...
            </div>
        """

    if result["status"] == "completed":
        return f"""
            <div class="bg-green-50 p-4 rounded-xl border border-green-200 flex flex-col md:flex-row justify-between items-center gap-4">
                <div class="flex items-center gap-3 text-green-700 font-bold">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    <span>Podcast Pronto: {result['title']}</span>
                </div>
                <a href="{result['download_url']}" download class="bg-green-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-green-700 transition shadow-md">
                    Scarica MP3
                </a>
            </div>
        """

    return f"<div class='p-4 bg-red-50 text-red-700 rounded-xl border border-red-200'>Errore: {result.get('message', 'Errore generico')}</div>"

@app.post("/preview", response_class=HTMLResponse)
async def preview(
    request: Request,
    article_urls: List[str] = Form(...),
    newsletter_url: str = Form(...)
):
    if not check_auth(request):
        return HTMLResponse("Unauthorized", status_code=401)
    cfg = Config(newsletter_url=newsletter_url)
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            newsletters = []
            for url in article_urls:
                link = {"href": url, "text": "Articolo"}
                nl = await fetch_content(context, link)
                newsletters.append(nl)
            await browser.close()

        if len(newsletters) == 1:
            script = await generate_script_daily(cfg, newsletters[0])
        else:
            script = await generate_script_weekly(cfg, newsletters)

        return f"""
            <div class="bg-gray-900 text-gray-100 p-6 rounded-2xl border border-gray-700 font-serif leading-relaxed whitespace-pre-wrap max-h-[500px] overflow-y-auto shadow-inner">
                {script}
            </div>
        """
    except Exception as e:
        return f"<div class='p-4 bg-red-50 text-red-700 rounded-xl border border-red-200'>Errore durante la preview: {str(e)}</div>"

@app.get("/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    if folder not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Cartella non valida")

    # Prevenzione path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nome file non valido")

    cfg = Config()
    path = cfg.output_dir / folder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    return FileResponse(path, filename=filename, media_type="audio/mpeg")
