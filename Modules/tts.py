import pyttsx3
from pathlib import Path
import io
import wave
import numpy as np


class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Set properties for better quality
        self.engine.setProperty('rate', 150)    # Speed of speech
        self.engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

    def synthesize(self, text: str, output_path: str = "output.wav") -> str:
        """
        Synthesize text to speech and save to file.
        Uses runAndWait() to ensure file is completely written before returning.
        """
        output_file = Path(output_path)
        
        # Clear any previous queue
        self.engine.stop()
        
        # Save to file
        self.engine.save_to_file(text, str(output_file))
        
        # CRITICAL: Wait for the file to be written
        # This blocks until pyttsx3 finishes writing
        self.engine.runAndWait()
        
        # Verify file was created and has content
        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError(f"TTS failed to generate audio file: {output_path}")
        
        return str(output_file)
    
    def get_available_voices(self):
        """Get list of available voices for debugging"""
        voices = self.engine.getProperty('voices')
        return [(v.id, v.name) for v in voices]
    
    def set_voice(self, voice_id: str):
        """Set specific voice by ID"""
        self.engine.setProperty('voice', voice_id)