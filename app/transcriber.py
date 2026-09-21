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
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False
        )
        formatted_segments = []
        MAX_WORDS_PER_CAPTION = 4
        
        for segment in segments:
            if not segment.words:
                formatted_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": []
                })
                continue
                
            # Chunk words into smaller captions
            current_chunk_words = []
            
            for w in segment.words:
                current_chunk_words.append({"start": w.start, "end": w.end, "word": w.word})
                
                # Check if we should split (hit max words, or it's the last word of a sentence)
                is_sentence_end = w.word.strip().endswith(('.', '!', '?'))
                
                if len(current_chunk_words) >= MAX_WORDS_PER_CAPTION or is_sentence_end:
                    chunk_text = "".join(word["word"] for word in current_chunk_words).strip()
                    formatted_segments.append({
                        "start": current_chunk_words[0]["start"],
                        "end": current_chunk_words[-1]["end"],
                        "text": chunk_text,
                        "words": current_chunk_words
                    })
                    current_chunk_words = []
            
            # Add any remaining words as a chunk
            if current_chunk_words:
                chunk_text = "".join(word["word"] for word in current_chunk_words).strip()
                formatted_segments.append({
                    "start": current_chunk_words[0]["start"],
                    "end": current_chunk_words[-1]["end"],
                    "text": chunk_text,
                    "words": current_chunk_words
                })

        return {
            "language": info.language,
            "duration": info.duration,
            "segments": formatted_segments
        }

transcriber = WhisperTranscriber()
