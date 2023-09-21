# H2O_Transcribe

H2O_Transcribe leverages the Whisper model, a versatile speech recognition model trained on 680,000 hours of multilingual and multitask supervised data sourced from the web. It is designed to comprehend multiple languages, making it a universal solution. For more information, visit [github.com/openai/whisper](https://github.com/openai/whisper/).

## Acknowledgments

This project has greatly benefited from the following repository:

- [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice): This repository has been extensively used in our project.

## Usage

H2O_Transcribe is now available on Docker Hub. You can find the latest version of this repository on Docker Hub for both CPU and GPU.

For CPU, visit: <https://hub.docker.com/r/aminsedaghat/h2o_transcribe>

To pull and run the Docker image for CPU, use the following commands:

```sh
docker pull aminsedaghat/h2o_transcribe:1.0
docker run -d -p 9000:9000 -e ASR_MODEL=base -e ASR_ENGINE=h2o_whisper aminsedaghat/h2o_transcribe:1.0
```

For GPU, visit: <https://hub.docker.com/r/aminsedaghat/h2o_transcribe-gpu>

To pull and run the Docker image for GPU, use the following commands:

```sh
docker pull aminsedaghat/h2o_transcribe-gpu:1.0
docker run -d --gpus all -p 9000:9000 -e ASR_MODEL=base -e ASR_ENGINE=h2o_whisper aminsedaghat/h2o_transcribe-gpu:1.0
```

Available ASR_MODELs include `tiny`, `base`, `small`, `medium`, `large`, `large-v1`, and `large-v2`. Note that `large` and `large-v2` are identical models.

For English-only applications, the `.en` models tend to perform better, particularly the `tiny.en` and `base.en` models. The difference becomes less significant for the `small.en` and `medium.en` models.

To use Docker Compose:

For CPU:
```sh
docker-compose up --build
```

For GPU:
```sh
docker-compose up --build -f docker-compose.gpu.yml
```

## Quick Start

After running the Docker image, interactive Swagger API documentation is available at [localhost:9000/docs](http://localhost:9000/docs).

## Automatic Speech Recognition Service (/asr)

The **transcribe** task transcribes the uploaded file. Both audio and video files are supported (as long as they are supported by ffmpeg).

You can get TXT, VTT, SRT, TSV, and JSON output as a file from the /asr endpoint. The language can be provided or it will be automatically recognized.

If you choose the **translate** task, it will provide an English transcript regardless of the spoken language.

You can enable word level timestamps output by using the `word_timestamps` parameter (only with `Faster Whisper` for now).

The service returns a JSON with the following fields:

- **text**: Contains the full transcript
- **segments**: Contains an entry per segment. Each entry provides `timestamps`, `transcript`, `token ids`, `word level timestamps`, and other metadata
- **language**: Detected or provided language (as a language code)

## Language Detection Service (/detect-language)

This service detects the language spoken in the uploaded file. For longer files, it only processes the first 30 seconds.

The service returns a JSON with the following fields:

- **detected_language**
- **language_code**

## Logging

The log file, named h2o-transcribe.log, can be found in the app folder. The default value is INFO (A docker argument will be added in next version to set the log level).

## Docker Build

### For CPU

```sh
# Build Image
docker build -t h2o_transcribe .

# Run Container
docker run -d -p 9000:9000 h2o_transcribe
# or
docker run -d -p 9001:9000 -e ASR_MODEL=base h2o_transcribe
```

### For GPU

```sh
# Build Image
docker build -f Dockerfile.gpu -t h2o_transcribe_gpu .

# Run Container
docker run -d --gpus all -p 9000:9000 h2o_transcribe_gpu
# or
docker run -d --gpus all -p 9000:9000 -e ASR_MODEL=base h2o_transcribe_gpu
```