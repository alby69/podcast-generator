from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from podcast_generator.config import Settings
from podcast_generator.exceptions import TranslationError

SYSTEM_PROMPT = """Sei un autore e conduttore di podcast tecnologici italiani.

Il tuo compito è prendere una o più newsletter tecniche in inglese e trasformarle
in un coinvolgente script per un podcast in italiano.

REGOLE:
- Traduci in italiano, ma adatta il tono all'ascolto: colloquiale, dinamico, entusiasta
- Non elencare i tool in modo freddo: presentali con transizioni naturali
  ("Oggi parliamo di un tool pazzesco che...", "Passiamo ora a...")
- Se ci sono più newsletter, uniscile in un unico episodio settimanale
  creando macro-categorie e rimuovendo duplicati
- Inizia direttamente con "Ciao a tutti e benvenuti a un nuovo episodio di..."
- Non aggiungere NOTE, INTRODUZIONI o commenti meta (es. "Ecco lo script")
- Produci solo il testo da leggere, senza markup o istruzioni di regia
- Ogni episodio deve essere un monologo fluido e piacevole da ascoltare"""


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, model: str, system_prompt: str, prompt: str
    ) -> str:
        ...


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self, model: str, system_prompt: str, prompt: str
    ) -> str:
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"system_instruction": system_prompt},
            )
            return response.text.strip()
        except Exception as e:
            raise TranslationError(f"Gemini API error: {e}") from e


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self, model: str, system_prompt: str, prompt: str
    ) -> str:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise TranslationError(f"OpenAI API error: {e}") from e


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate(
        self, model: str, system_prompt: str, prompt: str
    ) -> str:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8192,
            )
            return response.content[0].text.strip()
        except Exception as e:
            raise TranslationError(f"Anthropic API error: {e}") from e


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def generate(
        self, model: str, system_prompt: str, prompt: str
    ) -> str:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                    timeout=300,
                )
                response.raise_for_status()
                return response.json()["message"]["content"].strip()
        except Exception as e:
            raise TranslationError(f"Ollama API error: {e}") from e


def get_llm_provider(cfg: Settings) -> LLMProvider:
    providers = {
        "gemini": lambda: GeminiProvider(cfg.gemini_api_key),
        "openai": lambda: OpenAIProvider(cfg.openai_api_key),
        "anthropic": lambda: AnthropicProvider(cfg.anthropic_api_key),
        "ollama": lambda: OllamaProvider(cfg.ollama_base_url),
    }
    provider_fn = providers.get(cfg.llm_provider)
    if not provider_fn:
        raise TranslationError(
            f"Unknown LLM provider '{cfg.llm_provider}'. "
            f"Choose from: {', '.join(providers)}"
        )
    return provider_fn()


def _get_model(cfg: Settings) -> str:
    models = {
        "gemini": cfg.gemini_model,
        "openai": cfg.openai_model,
        "anthropic": cfg.anthropic_model,
        "ollama": cfg.ollama_model,
    }
    return models.get(cfg.llm_provider, cfg.gemini_model)


def _build_generation_config(cfg: Settings) -> dict:
    config = {"system_instruction": SYSTEM_PROMPT}
    if cfg.use_web_search and cfg.llm_provider == "gemini":
        config["tools"] = [{"google_search": {}}]
    return config


async def translate_newsletter(
    cfg: Settings, text: str
) -> str:
    provider = get_llm_provider(cfg)
    model = _get_model(cfg)

    if cfg.use_web_search:
        prompt = (
            f"Testo da convertire in podcast:\n\n{text}\n\n"
            "IMPORTANTE: Usa Google Search per approfondire ogni notizia citata, "
            "aggiungendo dettagli tecnici, contesto e curiosità recenti."
        )
    else:
        prompt = f"Testo da convertire in podcast:\n\n{text}"

    return await provider.generate(model, SYSTEM_PROMPT, prompt)


async def translate_multiple(
    cfg: Settings, newsletters: list[tuple[str, str]]
) -> str:
    provider = get_llm_provider(cfg)
    model = _get_model(cfg)

    combined = "\n\n--- NUOVA NEWSLETTER ---\n\n".join(
        f"TITOLO: {title}\nTESTO:\n{content}"
        for title, content in newsletters
    )

    prompt = (
        "Qui ci sono PIU' newsletter da unire in un unico episodio podcast "
        "settimanale. Riorganizzale per argomento, elimina duplicati e crea "
        "un monologo fluido.\n\n"
        f"{combined}"
    )

    if cfg.use_web_search:
        prompt += (
            "\n\nIMPORTANTE: Usa Google Search per approfondire gli argomenti principali, "
            "aggiungendo dettagli tecnici e contesto aggiornato."
        )

    return await provider.generate(model, SYSTEM_PROMPT, prompt)
