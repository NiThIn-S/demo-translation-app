const state = {
    mediaRecorder: null,
    recordedChunks: [],
    recordedBlob: null,
    recordingTimer: null,
    recordingStartedAt: null,
    recordingStream: null,
    recordedAudioUrl: null,
    maxRecordingSeconds: 30,
    isTranscribing: false,
};

const sourceLanguage = document.getElementById("source-language");
const targetLanguage = document.getElementById("target-language");

const translationForm = document.getElementById("translation-form");
const transcriptionForm = document.getElementById("transcription-form");

const translationText = document.getElementById("translation-text");
const audioFile = document.getElementById("audio-file");

const recordButton = document.getElementById("record-button");
const transcriptionSubmitButton =
    transcriptionForm?.querySelector('button[type="submit"]');

const recordingStatus = document.getElementById("recording-status");
const recordedAudio = document.getElementById("recorded-audio");

const translationResult = document.getElementById("translation-result");
const transcriptionResult = document.getElementById("transcription-result");

const transcriptionState = document.getElementById(
    "transcription-state",
);

const transcriptionMetadata = document.getElementById(
    "transcription-metadata",
);

const globalError = document.getElementById("global-error");

document.addEventListener("DOMContentLoaded", async () => {
    await loadLanguages();
});

async function loadLanguages() {
    try {
        const response = await fetch("/languages");


        if (!response.ok) {
            throw new Error("Unable to load languages.");
        }

        const languages = await response.json();

        for (const language of languages) {
            const sourceOption = document.createElement("option");
            sourceOption.value = language.code;
            sourceOption.textContent = language.name;

            sourceLanguage.appendChild(sourceOption);

            const targetOption = document.createElement("option");
            targetOption.value = language.code;
            targetOption.textContent = language.name;

            targetLanguage.appendChild(targetOption);
        }

        targetLanguage.value = "de";
    } catch (error) {
        showError(error.message);
    }


}


translationForm.addEventListener("submit", async (event) => {
    event.preventDefault();


    clearError();

    translationResult.textContent = "Translating...";
    translationResult.hidden = false;

    try {
        const response = await fetch("/translate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                text: translationText.value,
                source_language: sourceLanguage.value,
                target_language: targetLanguage.value,
            }),
        });

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            throw new Error(
                data.error?.message || "Translation failed.",
            );
        }

        translationResult.textContent =
            `${getLanguageName(data.source_language)} (${data.source_language}) → ` +
            `${getLanguageName(data.target_language)} (${data.target_language})\n\n` +
            data.translated_text;

        translationResult.hidden = false;
    } catch (error) {
        translationResult.hidden = true;
        showError(
            error.message || "Translation failed.",
        );
    }


});


audioFile.addEventListener("change", () => {
    if (!audioFile.files.length) {
        return;
    }


    clearRecordedAudio();

    recordingStatus.textContent = "Audio file selected";

    clearError();


});



transcriptionForm.addEventListener("submit", async (event) => {
    event.preventDefault();


    if (state.isTranscribing) {
        return;
    }

    clearError();
    clearTranscriptionResult();

    let file = audioFile.files[0];

    if (!file && state.recordedBlob) {
        file = createRecordedFile();
    }

    if (!file) {
        showError(
            "Please select an audio file or record audio.",
        );
        setTranscriptionState(
            "error",
            "No audio selected.",
        );
        return;
    }

    state.isTranscribing = true;

    setTranscriptionControlsDisabled(true);

    setTranscriptionState(
        "uploading",
        "Uploading file",
    );

    try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/transcribe", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await parseResponse(response);

            throw new Error(
                errorData.error?.message ||
                errorData.message ||
                "Transcription failed.",
            );
        }

        await consumeTranscriptionStream(response);
    } catch (error) {
        /*
         * This catches transport/network failures.
         *
         * Application-level errors emitted as NDJSON are handled
         * inside consumeTranscriptionStream().
         */
        setTranscriptionState(
            "error",
            error.message || "Transcription failed.",
        );

        showError(
            error.message || "Transcription failed.",
        );
    } finally {
        state.isTranscribing = false;
        setTranscriptionControlsDisabled(false);
    }


});

/*

* Consume application/x-ndjson incrementally.
*
* Every line from the backend is processed immediately:
*
* {"event":"update",...}
* {"event":"update",...}
* {"event":"error",...}
* {"event":"data",...}
*/

async function consumeTranscriptionStream(response) {
    const contentType =
        response.headers.get("content-type") || "";


    if (
        !contentType.includes("application/x-ndjson") &&
        !contentType.includes("application/ndjson")
    ) {
        /*
         * Keep this fallback so the UI remains usable if the server
         * returns JSON instead of NDJSON.
         */
        const data = await parseResponse(response);

        if (!response.ok) {
            throw new Error(
                data.error?.message ||
                data.message ||
                "Transcription failed.",
            );
        }

        if (data.text) {
            renderTranscriptionResult({
                transcript: data.text,
            });
        }

        setTranscriptionState(
            "completed",
            "Transcription completed",
        );

        return;
    }

    if (!response.body) {
        throw new Error(
            "The browser does not support streaming responses.",
        );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";

    try {
        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                break;
            }

            buffer += decoder.decode(
                value,
                { stream: true },
            );

            const lines = buffer.split("\n");

            /*
             * Keep the final incomplete line in the buffer.
             */
            buffer = lines.pop() || "";

            for (const line of lines) {
                processTranscriptionEvent(line);
            }
        }

        /*
         * Flush any remaining decoder state.
         */
        buffer += decoder.decode();

        if (buffer.trim()) {
            processTranscriptionEvent(buffer);
        }
    } finally {
        reader.releaseLock();
    }


}

function getRecordedFile() {
    if (!state.recordedBlob) {
        return null;
    }

    const mimeType = state.recordedBlob.type || "audio/webm";

    let extension = "webm";

    if (mimeType.includes("ogg")) {
        extension = "ogg";
    } else if (mimeType.includes("mp4")) {
        extension = "m4a";
    } else if (mimeType.includes("mpeg")) {
        extension = "mp3";
    }

    return new File(
        [state.recordedBlob],
        `browser-recording.${extension}`,
        {
            type: mimeType,
            lastModified: Date.now(),
        },
    );
}

function processTranscriptionEvent(line) {
    const trimmedLine = line.trim();


    if (!trimmedLine) {
        return;
    }

    let event;

    try {
        event = JSON.parse(trimmedLine);
    } catch (error) {
        console.error(
            "Invalid NDJSON event:",
            trimmedLine,
            error,
        );

        return;
    }

    /*
     * Status/update event.
     */
    if (event.event === "update") {
        setTranscriptionState(
            event.state || "processing",
            event.msg || formatState(event.state),
        );

        return;
    }

    /*
     * Error event.
     */
    if (event.event === "error") {
        const message =
            event.msg ||
            event.message ||
            "Transcription failed.";

        setTranscriptionState(
            "error",
            message,
        );

        showError(message);

        /*
         * Do not leave the UI visually stuck in "processing".
         */
        setTranscriptionControlsDisabled(false);

        return;
    }

    /*
     * Final data event.
     */
    if (event.event === "data") {
        if (event.state === "result") {
            renderTranscriptionResult(event);

            setTranscriptionState(
                "completed",
                "Transcription completed",
            );
        }

        return;
    }

    /*
     * Unknown event types are ignored rather than breaking
     * the stream.
     */
    console.debug(
        "Unknown transcription event:",
        event,
    );


}

function renderTranscriptionResult(data) {
    transcriptionResult.innerHTML = "";


    const transcript = document.createElement("div");

    transcript.className = "transcript-text";
    transcript.textContent =
        data.transcript ||
        data.text ||
        "";

    transcriptionResult.appendChild(transcript);

    transcriptionResult.hidden = false;

    renderTranscriptionMetadata(data);


}

function renderTranscriptionMetadata(data) {
    transcriptionMetadata.innerHTML = "";


    const metadata = [
        {
            label: "Detected language",
            value: data.detected_language,
        },
        {
            label: "Confidence",
            value: formatConfidence(data.confidence),
        },
        {
            label: "Backend",
            value: data.backend,
        },
    ];

    for (const item of metadata) {
        if (
            item.value === undefined ||
            item.value === null ||
            item.value === ""
        ) {
            continue;
        }

        const row = document.createElement("div");

        row.className = "metadata-row";

        const key = document.createElement("span");

        key.className = "metadata-key";
        key.textContent = item.label;

        const value = document.createElement("span");

        value.className = "metadata-value";
        value.textContent = item.value;

        row.appendChild(key);
        row.appendChild(value);

        transcriptionMetadata.appendChild(row);
    }

    transcriptionMetadata.hidden =
        transcriptionMetadata.children.length === 0;


}



function getLanguageName(code) {
    if (!code) {
        return "";
    }

    const option = Array.from(sourceLanguage.options).find(
        (option) => option.value === code,
    );

    if (option) {
        return option.textContent;
    }

    const targetOption = Array.from(targetLanguage.options).find(
        (option) => option.value === code,
    );

    if (targetOption) {
        return targetOption.textContent;
    }

    return code;
}

function formatConfidence(value) {
    if (
        typeof value !== "number" ||
        Number.isNaN(value)
    ) {
        return value ?? "";
    }


    return `${(value * 100).toFixed(2)}%`;


}



recordButton.addEventListener("click", async () => {
    if (state.mediaRecorder?.state === "recording") {
        stopRecording();
        return;
    }


    await startRecording();


});

async function startRecording() {
    clearError();


    if (state.isTranscribing) {
        return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
        showError(
            "Microphone recording is not supported by this browser.",
        );

        return;
    }

    if (!window.MediaRecorder) {
        showError(
            "Media recording is not supported by this browser.",
        );

        return;
    }

    /*
     * Recording is a mutually exclusive input.
     *
     * If a file was previously selected, clear it before
     * requesting the microphone.
     */
    clearSelectedFile();
    clearRecordedAudio();

    try {
        const stream =
            await navigator.mediaDevices.getUserMedia({
                audio: true,
            });

        const mimeType =
            getSupportedRecordingMimeType();

        const recorder = mimeType
            ? new MediaRecorder(
                stream,
                { mimeType },
            )
            : new MediaRecorder(stream);

        state.mediaRecorder = recorder;
        state.recordingStream = stream;
        state.recordedChunks = [];
        state.recordedBlob = null;

        recorder.addEventListener(
            "dataavailable",
            (event) => {
                if (event.data.size > 0) {
                    state.recordedChunks.push(
                        event.data,
                    );
                }
            },
        );

        recorder.addEventListener(
            "stop",
            () => {
                finishRecording(recorder);
            },
            { once: true },
        );

        recorder.start(250);

        state.recordingStartedAt = Date.now();

        recordButton.textContent = "Stop recording";
        recordingStatus.textContent =
            `Recording: 0s / ${state.maxRecordingSeconds}s`;

        state.recordingTimer =
            window.setInterval(() => {
                const elapsedSeconds =
                    Math.floor(
                        (
                            Date.now() -
                            state.recordingStartedAt
                        ) / 1000,
                    );

                recordingStatus.textContent =
                    `Recording: ${elapsedSeconds}s / ` +
                    `${state.maxRecordingSeconds}s`;

                if (
                    elapsedSeconds >=
                    state.maxRecordingSeconds
                ) {
                    stopRecording();
                }
            }, 250);
    } catch (error) {
        stopRecordingTracks();

        showError(
            error.message ||
            "Unable to access the microphone.",
        );

        recordingStatus.textContent = "Ready";
    }


}

function finishRecording(recorder) {
    stopRecordingTracks();


    const actualMimeType =
        recorder.mimeType ||
        getSupportedRecordingMimeType() ||
        "audio/webm";

    if (!state.recordedChunks.length) {
        state.recordedBlob = null;

        recordingStatus.textContent =
            "No audio recorded";

        return;
    }

    /*
     * Important:
     *
     * Create one complete Blob only after MediaRecorder has
     * emitted all chunks.
     */
    state.recordedBlob = new Blob(
        state.recordedChunks,
        {
            type: actualMimeType,
        },
    );

    /*
     * Revoke the previous URL before creating another one.
     */
    revokeRecordedAudioUrl();

    state.recordedAudioUrl =
        URL.createObjectURL(
            state.recordedBlob,
        );

    recordedAudio.src =
        state.recordedAudioUrl;

    recordedAudio.type =
        actualMimeType;

    recordedAudio.hidden = false;

    /*
     * Calling load() makes browsers reliably recognize the
     * newly-created Blob URL as a new media source.
     */
    recordedAudio.load();

    recordingStatus.textContent =
        "Recording ready";

    recordButton.textContent =
        "Start recording";


}

function stopRecording() {
    const recorder = state.mediaRecorder;


    if (!recorder) {
        stopRecordingTracks();

        return;
    }

    if (recorder.state === "recording") {
        recorder.stop();
    }

    if (state.recordingTimer) {
        window.clearInterval(
            state.recordingTimer,
        );

        state.recordingTimer = null;
    }

    recordButton.textContent =
        "Start recording";

    recordingStatus.textContent =
        "Finalizing recording...";


}

function stopRecordingTracks() {
    if (!state.recordingStream) {
        return;
    }


    for (
        const track of state.recordingStream.getTracks()
    ) {
        track.stop();
    }

    state.recordingStream = null;


}

function getSupportedRecordingMimeType() {
    const candidates = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg",
    ];


    return candidates.find(
        (type) =>
            MediaRecorder.isTypeSupported(type),
    ) || "";


}



function clearSelectedFile() {
    audioFile.value = "";
}

function clearRecordedAudio() {
    if (
        state.mediaRecorder?.state ===
        "recording"
    ) {
        stopRecording();
    }


    stopRecordingTracks();

    if (state.recordingTimer) {
        window.clearInterval(
            state.recordingTimer,
        );

        state.recordingTimer = null;
    }

    state.recordedChunks = [];
    state.recordedBlob = null;
    state.recordingStartedAt = null;

    revokeRecordedAudioUrl();

    recordedAudio.removeAttribute("src");
    recordedAudio.load();
    recordedAudio.hidden = true;

    recordButton.textContent =
        "Start recording";

    recordingStatus.textContent =
        "Ready";


}

function revokeRecordedAudioUrl() {
    if (state.recordedAudioUrl) {
        URL.revokeObjectURL(
            state.recordedAudioUrl,
        );


        state.recordedAudioUrl = null;
    }


}

function createRecordedFile() {
    const mimeType =
        state.recordedBlob.type ||
        "audio/webm";


    let extension = "webm";

    if (mimeType.includes("ogg")) {
        extension = "ogg";
    } else if (mimeType.includes("wav")) {
        extension = "wav";
    }

    return new File(
        [state.recordedBlob],
        `browser-recording.${extension}`,
        {
            type: mimeType,
            lastModified: Date.now(),
        },
    );


}

function setTranscriptionState(
    stateName,
    message,
) {
    if (!transcriptionState) {
        return;
    }


    transcriptionState.dataset.state =
        stateName;

    transcriptionState.textContent =
        message;

    transcriptionState.hidden = false;


}

function setTranscriptionControlsDisabled(
    disabled,
) {
    if (transcriptionSubmitButton) {
        transcriptionSubmitButton.disabled =
            disabled;
    }


    audioFile.disabled = disabled;

    /*
     * Keep the recording button usable while the
     * recording itself is active, but prevent starting
     * another recording during transcription.
     */
    if (
        disabled &&
        state.mediaRecorder?.state !== "recording"
    ) {
        recordButton.disabled = true;
    } else {
        recordButton.disabled = false;
    }


}

function clearTranscriptionResult() {
    transcriptionResult.textContent = "";
    transcriptionResult.hidden = true;


    transcriptionMetadata.innerHTML = "";
    transcriptionMetadata.hidden = true;


}

function formatState(stateName) {
    const labels = {
        uploading: "Uploading file",
        uploaded: "File uploaded",
        processing: "Processing audio",
        completed: "Transcription completed",
        error: "Transcription failed",
    };


    return (
        labels[stateName] ||
        "Processing..."
    );


}

async function parseResponse(response) {
    const contentType =
        response.headers.get("content-type") || "";


    if (
        contentType.includes("application/json")
    ) {
        return response.json();
    }

    return {
        error: {
            message: await response.text(),
        },
    };


}

async function parseJsonResponse(response) {
    return parseResponse(response);
}

function showError(message) {
    globalError.textContent =
        message || "An unexpected error occurred.";


    globalError.hidden = false;


}

function clearError() {
    globalError.textContent = "";
    globalError.hidden = true;
}


window.addEventListener(
    "beforeunload",
    () => {
        revokeRecordedAudioUrl();
        stopRecordingTracks();
    },
);
