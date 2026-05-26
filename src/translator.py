from google import genai

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


def translate_newsletter(
    api_key: str, model: str, text: str, use_search: bool = False
) -> str:
    client = genai.Client(api_key=api_key)

    config = {"system_instruction": SYSTEM_PROMPT}
    if use_search:
        config["tools"] = [{"google_search": {}}]
        prompt = (
            f"Testo da convertire in podcast:\n\n{text}\n\n"
            "IMPORTANTE: Usa Google Search per approfondire ogni notizia citata, "
            "aggiungendo dettagli tecnici, contesto e curiosità recenti."
        )
    else:
        prompt = f"Testo da convertire in podcast:\n\n{text}"

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text.strip()


def translate_multiple(
    api_key: str, model: str, newsletters: list[tuple[str, str]], use_search: bool = False
) -> str:
    combined = "\n\n--- NUOVA NEWSLETTER ---\n\n".join(
        f"TITOLO: {title}\nTESTO:\n{content}" for title, content in newsletters
    )
    prompt = (
        "Qui ci sono PIU' newsletter da unire in un unico episodio podcast "
        "settimanale. Riorganizzale per argomento, elimina duplicati e crea "
        "un monologo fluido.\n\n"
        f"{combined}"
    )

    config = {"system_instruction": SYSTEM_PROMPT}
    if use_search:
        config["tools"] = [{"google_search": {}}]
        prompt += (
            "\n\nIMPORTANTE: Usa Google Search per approfondire gli argomenti principali, "
            "aggiungendo dettagli tecnici e contesto aggiornato."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text.strip()
