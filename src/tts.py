from pathlib import Path

import edge_tts


async def generate_audio(
    text: str,
    voice: str,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    return output_path


async def generate_audio_edge(
    text: str,
    voice: str,
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    return output_path


async def generate_audio(
    text: str,
    voice: str,
    output_path: str | Path,
    elevenlabs_api_key: str | None = None,
) -> Path:
    if elevenlabs_api_key:
        return await generate_audio_elevenlabs(
            elevenlabs_api_key, text, voice, output_path
        )
    else:
        return await generate_audio_edge(text, voice, output_path)
