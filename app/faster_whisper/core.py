import os
from typing import BinaryIO, Union, Optional
from io import StringIO
from threading import Lock
import torch
import whisper
from .utils import model_converter, ResultWriter, WriteTXT, WriteSRT, WriteVTT, WriteTSV, WriteJSON
from faster_whisper import WhisperModel
import logging

MODEL_NAME = os.getenv("ASR_MODEL", "base")
MODEL_PATH = os.path.join("/root/.cache/faster_whisper", MODEL_NAME)
BEAM_SIZE = 5

logger = logging.getLogger(__name__)

# Model setup
model_converter(MODEL_NAME, MODEL_PATH)
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float32" if device == "cuda" else "int8"
logger.info(f"Loading model in {device.upper()} mode.")
model = WhisperModel(MODEL_PATH, device=device, compute_type=compute_type)
model_lock = Lock()

OUTPUT_FORMATS = {
    "srt": WriteSRT,
    "vtt": WriteVTT,
    "tsv": WriteTSV,
    "json": WriteJSON,
    "txt": WriteTXT
}

def transcribe(
    audio,
    task: Optional[str],
    language: Optional[str],
    initial_prompt: Optional[str],
    word_timestamps: Optional[bool],
    output: Optional[str]
) -> StringIO:
    
    logger.info(f"Transcribing with task: {task}, language: {language}, initial_prompt: {initial_prompt}")
    options_dict = {"task": task}
    if language:
        options_dict["language"] = language
    if initial_prompt:
        options_dict["initial_prompt"] = initial_prompt
    if word_timestamps:
        options_dict["word_timestamps"] = True

    with model_lock:   
        segments = []
        text = ""
        segment_generator, info = model.transcribe(audio, beam_size=BEAM_SIZE, **options_dict)
        for segment in segment_generator:
            segments.append(segment)
            text += segment.text
        result = {
            "language": options_dict.get("language", info.language),
            "segments": segments,
            "text": text
        }

    outputFile = StringIO()
    write_result(result, outputFile, output)
    outputFile.seek(0)

    return outputFile

def language_detection(audio: BinaryIO) -> str:

    logger.info("Detecting language.")
    audio = whisper.pad_or_trim(audio)

    with model_lock:
        _, info = model.transcribe(audio, beam_size=BEAM_SIZE)
        detected_lang_code = info.language

    logger.info(f"Detected language code: {detected_lang_code}")
    return detected_lang_code

def write_result(result: dict, file: BinaryIO, output: Optional[str]) -> None:

    logger.info(f"Writing result to {output} format.")
    writer_class = OUTPUT_FORMATS.get(output)
    if writer_class:
        writer_class(ResultWriter).write_result(result, file=file)
    else:
        logger.error("Invalid output method selected.")
        raise ValueError('Please select a valid output method!')

