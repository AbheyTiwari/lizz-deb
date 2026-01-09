from TTS.api import TTS
from pathlib import Path
import torch


class TextToSpeech:
    def __init__(self):
        # Initialize Coqui TTS with a high-quality model
        # Using XTTS v2 for best quality multilingual support
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # You can change this to other models if needed
        # List available models with: TTS().list_models()
        self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC").to(device)
        
        # Alternative high-quality options:
        # self.tts = TTS("tts_models/en/vctk/vits").to(device)  # Multi-speaker
        # self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)  # Best quality, slower

    def synthesize(self, text: str, output_path: str = "output.wav") -> str:
        """
        Synthesize text to speech and save to file.
        Same interface as before to work with existing app.py calls.
        """
        output_file = Path(output_path)
        
        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate speech and save to file
        self.tts.tts_to_file(text=text, file_path=str(output_file))
        
        # Verify file was created and has content
        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError(f"TTS failed to generate audio file: {output_path}")
        
        return str(output_file)
    
    def get_available_voices(self):
        """Get list of available models/voices"""
        # For multi-speaker models, you can get speakers
        if hasattr(self.tts, 'speakers') and self.tts.speakers:
            return [(i, speaker) for i, speaker in enumerate(self.tts.speakers)]
        return [("default", "Default Voice")]
    
    def set_voice(self, voice_id: str):
        """Set specific voice/speaker (for multi-speaker models)"""
        if hasattr(self.tts, 'speakers') and self.tts.speakers:
            # voice_id should be speaker name for multi-speaker models
            self.speaker = voice_id
        # For single-speaker models, this is a no-op