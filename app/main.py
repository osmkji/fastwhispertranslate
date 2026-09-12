import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Depends
from app.auth import verify_api_key
from app.transcriber import transcriber
from app.schemas import TranscriptionResponse

app = FastAPI(title="Whisper Service for Laravel")

@app.get("/health")
def health_check():
    return {"status": "ok", "model": transcriber.model is not None}

@app.post("/transcribe", response_model=TranscriptionResponse, dependencies=[Depends(verify_api_key)])
async def transcribe_audio(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name
    try:
        result = transcriber.transcribe(temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
