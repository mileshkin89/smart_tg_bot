import subprocess
from pathlib import Path
import uuid
from settings.config import config


def convert_audio_for_stt(input_path: Path) -> Path:
    """
    Converts input audio file to Google STT-compatible format (OGG_OPUS, 16kHz, mono).

    Args:
        input_path (Path): Path to the original audio file.

    Returns:
        Path: Path to the converted audio file in OGG_OPUS format.

    Raises:
        RuntimeError: If FFmpeg conversion fails.
    """
    output_dir: Path = config.path_to_converted_audio_file
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{uuid.uuid4().hex}.ogg"

    command = [
        "ffmpeg",
        "-y",                 # Overwrite if file exists
        "-i", str(input_path),
        "-ar", "16000",       # Sample rate 16 kHz
        "-ac", "1",           # Mono channel
        "-c:a", "libopus",    # Audio codec for OGG
        str(output_path)
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"❌ FFmpeg failed to convert audio: {e}")

