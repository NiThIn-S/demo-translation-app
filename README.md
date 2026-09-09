# Translation & Transcription App

A small FastAPI web application providing text translation and speech-to-text through a simple browser UI.

The application uses a layered architecture with model providers isolated behind interfaces, allowing providers to be mocked for testing and replaced without changing the API or UI.

## Features

### Translation

* Translate short text between supported European languages.
* Source-language auto-detection.
* Target-language selection.
* Empty input and oversized input validation.
* Unsupported language pairs handled gracefully.
* Translation backend included in the response.
* Configurable inference timeout and concurrency limit.

### Transcription

* Upload WAV, MP3 and M4A audio files.
* Browser microphone recording.
* Audio validation, decoding and normalization.
* Automatic spoken-language detection.
* Streamed processing/status events.
* Detected language and confidence returned with the transcript.
* Configurable inference concurrency limit.
* Bounded retry when the transcription model is busy.

## Tech Stack

* Python 3.12
* FastAPI
* Pydantic
* Jinja2 + JavaScript
* `uv`
* Helsinki-NLP OPUS-MT
* faster-whisper
* Lingua
* pytest

## Architecture

The application follows a layered architecture:

```text
Browser UI
    |
    v
FastAPI Router
    |
    v
Service Layer
    |
    v
Provider / Adapter Interfaces
    |
    +--> Translation Provider --> OPUS-MT
    |
    +--> Detection Provider --> Lingua
    |
    +--> Transcription Provider --> faster-whisper
```

The router handles HTTP concerns, while application logic is implemented in services.

Model-specific logic is isolated behind provider interfaces. This allows production providers to be replaced with mocks during testing and makes it possible to add alternative backends without changing the UI.

## Translation

### Primary: Helsinki-NLP OPUS-MT

OPUS-MT was selected because individual language-pair models are relatively small, CPU-friendly, freely available, and do not require a paid API key.

The application currently supports:

* English (`en`)
* German (`de`)
* French (`fr`)
* Spanish (`es`)

Supported language pairs are explicitly configured.

Models are loaded lazily and reused after initialization.

### Backup: LibreTranslate

LibreTranslate is the planned backup translation backend.

It can be implemented behind the existing translation provider interface, allowing the backend to be changed without modifying the UI or service contract.

## Speech-to-Text

### Primary: faster-whisper

The application uses faster-whisper with the `tiny` model and CPU/int8 configuration.

It was selected because it provides practical CPU inference, has relatively low resource requirements, supports automatic language detection, and does not require a paid API key.

Uploaded audio is decoded and normalized to 16 kHz mono signed 16-bit PCM before inference.

### Backup: openai-whisper

The original `openai-whisper` implementation is the planned backup.

It provides the same Whisper model family but generally has higher CPU/runtime requirements than faster-whisper. The provider abstraction allows it to be added without changing the application layer.

## Language Detection

Text source-language detection uses Lingua.

Audio language detection is provided by Whisper.

Detection confidence is returned where available.

## Model Loading

Models are loaded lazily rather than during application startup.

Each provider protects model initialization with an async lock and reuses the loaded model instance.

This keeps startup lightweight and ensures tests do not require model downloads.

The first inference request may take longer when model artifacts need to be downloaded and initialized.

## Concurrency

Inference concurrency is controlled using configurable `MAX_INFLIGHT`.

Separate limiters are used for translation and transcription.

Translation requests fail fast with HTTP 429 when inference capacity is exhausted. Transcription requests perform a small bounded retry before returning a busy error.

The current limiter is intentionally in-process because the take-home is deployed as a single application process.

## API

### `GET /health`

Returns application health information.

### `GET /languages`

Returns supported languages and translation capabilities.

### `POST /translate`

Translates text between supported languages.

Example:

```json
{
  "text": "Hello, how are you?",
  "source_language": "auto",
  "target_language": "de"
}
```

### `POST /transcribe`

Accepts an audio file and streams newline-delimited JSON status/result events.

The final result includes:

* transcript
* detected language
* confidence
* backend

## Configuration

Runtime behaviour is configurable through environment/settings, including:

* `MAX_INFLIGHT`
* `INFERENCE_TIMEOUT_SECONDS`
* `MAX_TRANSLATION_CHARS`
* `MAX_FILE_SIZE_MB`
* `MAX_AUDIO_DURATION_SECONDS`
* `ASR_MODEL`
* `ASR_DEVICE`
* `ASR_COMPUTE_TYPE`

## Local Development

Python 3.11+ is required.

Install dependencies:

```bash
uv sync
```

Run the application:

```bash
./entrypoint.sh
```

The application will be available at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

The application can also be started directly with:

```bash
uv run uvicorn app.new_main:app --host 0.0.0.0 --port 8000
```

## Testing

Tests use mocked providers and do not download ML models.

Run:

```bash
uv run pytest -q
```

The test suite covers service behaviour, API endpoints, validation and error handling.

## Deployment

The take-home application is designed to run as a single web service.

Render configuration:

**Build command**

```bash
uv sync --frozen
```

**Start command**

```bash
./entrypoint.sh
```

**Health check path**

```text
/health
```

The application uses one process because model instances and the concurrency limiters are held in application memory.

The Render free tier has limited CPU/RAM and an ephemeral filesystem, so model artifacts may need to be downloaded again after a restart or spin-down.

## Production Considerations

For a production deployment, I would evolve the current provider architecture into independently deployable model services.

Each model/service could have its own resource limits, scaling configuration and deployment lifecycle. The application API would communicate with the selected model service through a stable provider/client interface.

Other production improvements would include:

* Distributed rate limiting and model-specific concurrency control.
* Circuit breakers, bounded retries and exponential backoff.
* Authentication and per-user/per-tenant quotas for public APIs.
* Persistent/shared model artifacts or pre-baked model images.
* ONNX conversion and quantization where beneficial, validated against a representative quality benchmark.
* Model-specific CPU/GPU optimization and resource tuning.
* Queue-based processing for longer transcription jobs.
* Metrics, tracing and structured observability.
* Model versioning and controlled rollouts.
* Additional integration and load testing.
* Automatic provider fallback and health-based model routing.

These are intentionally not implemented in the take-home because the assignment does not require production infrastructure.

## Limitations and Trade-offs

* CPU inference can be slow.
* The smallest Whisper model is used to keep resource requirements reasonable.
* Translation models are loaded per language pair as needed.
* The free-tier deployment does not provide persistent model storage.
* Browser recording depends on browser-supported `MediaRecorder` formats.
* The application is intended for short translation text and short audio.
* There is no persistent job queue.
* Transcript-to-translation chaining is not currently implemented.
* Partial transcript streaming is not currently implemented; the transcription endpoint streams processing/status events.

The implementation prioritizes clean structure, testability and a working end-to-end product within the assignment timebox.

## AI Assistance

AI coding assistance was used during development, and test implementation.

The overall application architecture, design decisions, technology choices, and implementation approach were defined by me. The resulting implementation was reviewed and tested during development.