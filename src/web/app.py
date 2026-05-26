import os
import asyncio
import uuid
from pathlib import Path
from typing import List
from datetime import datetime

from fastapi import FastAPI, Request, Form, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from playwright.async_api import async_playwright

from src.config import Config
from src.fetcher import get_article_list, _fetch_content
from src.builder import _slugify, _save_script
from src.translator import translate_newsletter, translate_multiple
from src.tts import generate_audio
from src.audio import add_intro_outro, check_duration, merge_audio_files
from src.web.db import create_db_and_tables, get_session, EpisodeDB, engine

app = FastAPI(title="Podcast Generator Web")

# Assicurati che le directory di output esistano
cfg_default = Config()
(cfg_default.output_dir / "daily").mkdir(parents=True, exist_ok=True)
(cfg_default.output_dir / "weekly").mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory="src/web/templates")

generation_results = {}

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends(get_session)):
    episodes = session.exec(select(EpisodeDB).order_by(EpisodeDB.created_at.desc())).all()
    return templates.TemplateResponse(request, "index.html", {"episodes": episodes})

@app.post("/fetch-articles", response_class=HTMLResponse)
async def fetch_articles(request: Request, newsletter_url: str = Form(...)):
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
    cfg = Config(newsletter_url=newsletter_url)
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            newsletters = []
            for url in article_urls:
                link = {"href": url, "text": "Articolo"}
                nl = await _fetch_content(browser, link)
                newsletters.append(nl)
            await browser.close()

        today = datetime.now()
        if len(newsletters) == 1:
            nl = newsletters[0]
            script = translate_newsletter(cfg.gemini_api_key, cfg.gemini_model, nl.content, use_search=cfg.use_web_search)
            date_str = nl.date.strftime("%Y-%m-%d")
            slug = _slugify(nl.title)
            folder = "daily"
            filename = f"{date_str}_{slug}_{job_id[:8]}.mp3"
            title = nl.title
            source_url = nl.url
        else:
            newsletter_items = [(n.title, n.content) for n in newsletters]
            script = translate_multiple(cfg.gemini_api_key, cfg.gemini_model, newsletter_items, use_search=cfg.use_web_search)
            folder = "weekly"
            filename = f"compilation_{today.strftime('%Y%m%d')}_{job_id[:8]}.mp3"
            title = f"Compilation {len(newsletters)} articoli"
            source_url = newsletter_url

        audio_path = cfg.output_dir / folder / filename
        script_path = cfg.output_dir / folder / f"{filename}.txt"

        await generate_audio(script, cfg.tts_voice, audio_path)
        if cfg.intro_path or cfg.outro_path:
            add_intro_outro(audio_path, cfg.intro_path, cfg.outro_path, audio_path)
        _save_script(script, script_path)

        # Persistenza nel DB
        with Session(engine) as session:
            new_ep = EpisodeDB(
                title=title,
                url=source_url,
                date=today.strftime("%Y-%m-%d"),
                audio_path=f"/download/{folder}/{filename}",
                script_path=str(script_path),
                created_at=datetime.now().isoformat()
            )
            session.add(new_ep)
            session.commit()
            session.refresh(new_ep)

        generation_results[job_id] = {
            "status": "completed",
            "download_url": f"/download/{folder}/{filename}",
            "filename": filename,
            "title": title
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

@app.get("/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    cfg = Config()
    path = cfg.output_dir / folder / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File non trovato")
    return FileResponse(path, filename=filename, media_type="audio/mpeg")
