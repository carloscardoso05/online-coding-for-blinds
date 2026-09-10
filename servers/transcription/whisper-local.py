import tempfile

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

app = FastAPI()

# --- Habilitar CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrega modelo Whisper uma vez
model = WhisperModel("turbo", device="auto", compute_type="auto")

@app.post("/transcrever")
async def transcrever(audio: UploadFile = File(...)):
    # Salva áudio temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    # Transcreve
    segmentos, _ = model.transcribe(tmp_path, language="pt")
    transcricao = " ".join(segmento.text.strip() for segmento in segmentos).strip()
    return {"transcricao": transcricao}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
