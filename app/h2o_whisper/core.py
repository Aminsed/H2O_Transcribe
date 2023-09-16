import os
from typing import BinaryIO, Optional
from io import StringIO
from threading import Lock
import torch
import whisper
from whisper.utils import ResultWriter, WriteTXT, WriteSRT, WriteVTT, WriteTSV, WriteJSON
import logging

MODEL_NAME = os.getenv("ASR_MODEL", "base")

logger = logging.getLogger(__name__)

# Model setup
if torch.cuda.is_available():
    logger.info("CUDA is available. Loading model in CUDA mode.")
    model = whisper.load_model(MODEL_NAME).cuda()
else:
    logger.info("CUDA is not available. Loading model in CPU mode.")
    model = whisper.load_model(MODEL_NAME)
model_lock = Lock()

OUTPUT_FORMATS = {
    "srt": WriteSRT,
    "vtt": WriteVTT,
    "tsv": WriteTSV,
    "json": WriteJSON,
    "txt": WriteTXT
}

def transcribe(
    audio: BinaryIO,
    task: Optional[str],
    language: Optional[str],
    initial_prompt: Optional[str],
    word_timestamps: Optional[bool],
    output: str
) -> StringIO:

    logger.info(f"Transcribing with task: {task}, language: {language}, initial_prompt: {initial_prompt}")
    options_dict = {"task": task}
    if language:
        options_dict["language"] = language
    if initial_prompt:
        options_dict["initial_prompt"] = initial_prompt
    if word_timestamps:
        options_dict["word_timestamps"] = word_timestamps

    with model_lock:
        result = model.transcribe(audio, **options_dict)

    outputFile = StringIO()
    write_result(result, outputFile, output)
    outputFile.seek(0)

    return outputFile

def language_detection(audio: BinaryIO) -> str:

    logger.info("Detecting language.")
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    with model_lock:
        _, probs = model.detect_language(mel)
    detected_lang_code = max(probs, key=probs.get)
    logger.info(f"Detected language code: {detected_lang_code}")

    return detected_lang_code

def write_result(result: dict, file: BinaryIO, output: str) -> None:

    logger.info(f"Writing result to {output} format.")
    writer_class = OUTPUT_FORMATS.get(output)
    if writer_class:
        writer_class(ResultWriter).write_result(result, file=file)
    else:
        logger.error("Invalid output method selected.")
        raise ValueError('Please select a valid output method!')
