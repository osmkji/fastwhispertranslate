from faster_whisper import WhisperModel
from app.config import settings

class WhisperTranscriber:
    def __init__(self):
        self.model = WhisperModel(
            settings.MODEL_SIZE,
            device=settings.DEVICE,
            compute_type=settings.COMPUTE_TYPE
        )

    def transcribe(self, file_path: str):
        segments, info = self.model.transcribe(
            file_path,
            beam_size=5,
            word_timestamps=True
        )
        formatted_segments = []
        for segment in segments:
            words = []
            if segment.words:
                words = [
                    {"start": w.start, "end": w.end, "word": w.word}
                    for w in segment.words
                ]
            formatted_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": words
            })
        return {
            "language": info.language,
            "duration": info.duration,
            "segments": formatted_segments
        }

transcriber = WhisperTranscriber()
