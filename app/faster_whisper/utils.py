import json
import logging
import os
from typing import TextIO

from ctranslate2.converters.transformers import TransformersConverter

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MILLISECONDS_IN_HOUR = 3_600_000
MILLISECONDS_IN_MINUTE = 60_000
MILLISECONDS_IN_SECOND = 1_000

from ctranslate2.converters.transformers import TransformersConverter

def model_converter(model, model_output):
    logger.info(f"Converting model: {model}")
    converter = TransformersConverter("openai/whisper-" + model)
    try:
        converter.convert(model_output, None, "float16", False)
    except Exception as e:
        logger.error(f"Model conversion failed: {e}")

def format_timestamp(seconds: float, always_include_hours: bool = False, decimal_marker: str = '.') -> str:
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // MILLISECONDS_IN_HOUR
    milliseconds -= hours * MILLISECONDS_IN_HOUR

    minutes = milliseconds // MILLISECONDS_IN_MINUTE
    milliseconds -= minutes * MILLISECONDS_IN_MINUTE

    seconds = milliseconds // MILLISECONDS_IN_SECOND
    milliseconds -= seconds * MILLISECONDS_IN_SECOND

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

    
class ResultWriter:
    extension: str

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def __call__(self, result: dict, audio_path: str):
        audio_basename = os.path.basename(audio_path)
        output_path = os.path.join(self.output_dir, audio_basename + "." + self.extension)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                self.write_result(result, file=f)
        except IOError as e:
            logger.error(f"Failed to write to file {output_path}: {e}")

    def write_result(self, result: dict, file: TextIO):
        raise NotImplementedError


class WriteTXT(ResultWriter):
    extension: str = "txt"

    def write_result(self, result: dict, file: TextIO):
        for segment in result["segments"]:
            print(segment.text.strip(), file=file, flush=True)


class WriteVTT(ResultWriter):
    extension: str = "vtt"

    def write_result(self, result: dict, file: TextIO):
        print("WEBVTT\n", file=file)
        for segment in result["segments"]:
            print(
                f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n"
                f"{segment.text.strip().replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


class WriteSRT(ResultWriter):
    extension: str = "srt"

    def write_result(self, result: dict, file: TextIO):
        for i, segment in enumerate(result["segments"], start=1):
            # write srt lines
            print(
                f"{i}\n"
                f"{format_timestamp(segment.start, always_include_hours=True, decimal_marker=',')} --> "
                f"{format_timestamp(segment.end, always_include_hours=True, decimal_marker=',')}\n"
                f"{segment.text.strip().replace('-->', '->')}\n",
                file=file,
                flush=True,
            )


class WriteTSV(ResultWriter):
    """
    Write a transcript to a file in TSV (tab-separated values) format containing lines like:
    <start time in integer milliseconds>\t<end time in integer milliseconds>\t<transcript text>

    Using integer milliseconds as start and end times means there's no chance of interference from
    an environment setting a language encoding that causes the decimal in a floating point number
    to appear as a comma; also is faster and more efficient to parse & store, e.g., in C++.
    """
    extension: str = "tsv"

    def write_result(self, result: dict, file: TextIO):
        print("start", "end", "text", sep="\t", file=file)
        for segment in result["segments"]:
            print(round(1000 * segment.start), file=file, end="\t")
            print(round(1000 * segment.end), file=file, end="\t")
            print(segment.text.strip().replace("\t", " "), file=file, flush=True)


class WriteJSON(ResultWriter):
    extension: str = "json"

    def write_result(self, result: dict, file: TextIO):
        json.dump(result, file)

