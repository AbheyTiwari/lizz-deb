import whisper
from pathlib import Path

_model_cache = {}
class SpeechRecognizer:
    def __init__(self, model_size: str = "base"):
        if model_size not in _model_cache:
            _model_cache[model_size] = whisper.load_model(model_size)
        self.model = _model_cache[model_size]

    def transcribe(self, audio_path: str) -> dict:
        audio_file = Path(audio_path)

        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        result = self.model.transcribe(str(audio_file))

        return {
            "text": result["text"].strip(),
            "language": result.get("language"),
        }
