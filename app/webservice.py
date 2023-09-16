import os
from os import path
import importlib.metadata
from typing import BinaryIO, Union

import numpy as np
import ffmpeg
from fastapi import FastAPI, File, UploadFile, Query, applications
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from whisper import tokenizer

import logging
logging.basicConfig(filename='h2o-transcribe.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ASR_ENGINE = os.getenv("ASR_ENGINE", "h2o_whisper")
if ASR_ENGINE == "faster_whisper":
    from .faster_whisper.core import transcribe, language_detection
else:
    from .h2o_whisper.core import transcribe, language_detection

SAMPLE_RATE=16000
LANGUAGE_CODES=sorted(list(tokenizer.LANGUAGES.keys()))

projectMetadata = importlib.metadata.metadata('h2o-transcribe')
app = FastAPI(
    title=projectMetadata['Name'].title().replace('-', ' '),
    description=projectMetadata['Summary'],
    version=projectMetadata['Version'],
    contact={
        "url": projectMetadata['Home-page']
    },
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

assets_path = os.getcwd() + "/swagger-ui-assets"
if path.exists(assets_path + "/swagger-ui.css") and path.exists(assets_path + "/swagger-ui-bundle.js"):
    app.mount("/assets", StaticFiles(directory=assets_path), name="static")
    def swagger_monkey_patch(*args, **kwargs):
        return get_swagger_ui_html(
            *args,
            **kwargs,
            swagger_favicon_url="",
            swagger_css_url="/assets/swagger-ui.css",
            swagger_js_url="/assets/swagger-ui-bundle.js",
        )
    applications.get_swagger_ui_html = swagger_monkey_patch

@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def index():
    logger.info("Redirecting to /docs")
    return "/docs"

@app.post("/asr", tags=["Endpoints"])
def asr(
    task : Union[str, None] = Query(default="transcribe", enum=["transcribe", "translate"]),
    language: Union[str, None] = Query(default=None, enum=LANGUAGE_CODES),
    initial_prompt: Union[str, None] = Query(default=None),
    audio_file: UploadFile = File(...),
    encode : bool = Query(default=True, description="Encode audio first through ffmpeg"),
    output : Union[str, None] = Query(default="txt", enum=["txt", "vtt", "srt", "tsv", "json"]),
    word_timestamps : bool = Query(
        default=False, 
        description="World level timestamps", 
        include_in_schema=(True if ASR_ENGINE == "faster_whisper" else False)
    )
):
    try:
        logger.info("ASR request received with params: %s", {
            "task": task,
            "language": language,
            "initial_prompt": initial_prompt,
            "audio_file": audio_file.filename,
        })
        
        audio = load_audio(audio_file.file, encode)
        result = transcribe(audio, task, language, initial_prompt, word_timestamps, output)
        result_str = result.getvalue()
        logger.info("ASR result of type %s with length %d", type(result_str), len(result_str))        
        
        return StreamingResponse(
            result,
            media_type="text/plain",
            headers={
                'Asr-Engine': ASR_ENGINE,
                'Content-Disposition': f'attachment; filename="{audio_file.filename}.{output}"'
            }
        )
    except Exception as e:
        logger.exception("ASR request failed with error: %s", str(e))
        raise e

@app.post("/detect-language", tags=["Endpoints"])
def detect_language(
    audio_file: UploadFile = File(...),
    encode : bool = Query(default=True, description="Encode audio first through ffmpeg")
):
    try:
        detected_lang_code = language_detection(load_audio(audio_file.file, encode))
        logger.info("Received language detection request")
        return {"detected_language": tokenizer.LANGUAGES[detected_lang_code], "language_code": detected_lang_code}
    except Exception as e:
        logger.exception("Language detection failed with error: %s", str(e))
        raise e

def load_audio(file: BinaryIO, encode: bool = True, sr: int = SAMPLE_RATE):
    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=file.read())
            )
        except ffmpeg.Error as e:
            logger.error(f"Failed to load audio: {e}")
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        out = file.read()

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
