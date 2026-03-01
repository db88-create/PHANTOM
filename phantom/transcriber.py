import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _detect_device() -> tuple[str, str]:
    """Auto-detect CUDA GPU, fall back to CPU with int8."""
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


class Transcriber:
    def __init__(self, model_size: str = "base"):
        device, compute_type = _detect_device()
        logger.info(
            "Loading Whisper model '%s' on %s (%s)", model_size, device, compute_type
        )
        self._model = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )

    def transcribe(self, audio: np.ndarray) -> str:
        segments, info = self._model.transcribe(audio, beam_size=5, vad_filter=True)
        # Segments is a generator; consume it
        texts = []
        for segment in segments:
            texts.append(segment.text.strip())
        return " ".join(texts).strip()
