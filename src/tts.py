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
