import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
MIN_DURATION_SEC = 0.5


class Recorder:
    def __init__(self, device: int | None = None):
        self._device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording:
            self._chunks.append(indata[:, 0].copy())

    def start(self):
        self._chunks = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=self._device,
                callback=self._audio_callback,
            )
            self._stream.start()
        except sd.PortAudioError:
            self._recording = False
            raise

    def stop(self) -> np.ndarray | None:
        if not self._recording:
            return None

        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._chunks:
            return None

        audio = np.concatenate(self._chunks)
        duration = len(audio) / SAMPLE_RATE

        if duration < MIN_DURATION_SEC:
            return None

        return audio
