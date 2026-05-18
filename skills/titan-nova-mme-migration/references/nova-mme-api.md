# Nova MME Complete API Reference

Model ID: `amazon.nova-2-multimodal-embeddings-v1:0`

Source of truth: <https://docs.aws.amazon.com/nova/latest/userguide/embeddings-schema.html>

---

## Top-level request fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `schemaVersion` | Optional | string | Default: `"nova-multimodal-embed-v1"` (only allowed value) |
| `taskType` | Required | string | `"SINGLE_EMBEDDING"` (sync) or `"SEGMENTED_EMBEDDING"` (async only) |
| `singleEmbeddingParams` | Required for sync | object | See below |
| `segmentedEmbeddingParams` | Required for async | object | See below |

---

## singleEmbeddingParams (sync — `InvokeModel`)

| Field | Required | Type | Notes |
|---|---|---|---|
| `embeddingPurpose` | Required | string | See full value table below |
| `embeddingDimension` | Optional | int | `256 \| 384 \| 1024 \| 3072`. Default: `3072` |
| `text` | Optional* | object | *Exactly one of text/image/video/audio must be present |
| `image` | Optional* | object | |
| `audio` | Optional* | object | |
| `video` | Optional* | object | |

---

## embeddingPurpose — all values

### Indexing (always use when building the vector store)

| Value | Use case |
|---|---|
| `"GENERIC_INDEX"` | Building an index of **any** modality (text, image, video, audio, document). Use this for all content being stored. |

### Retrieval (use at query time — match to what's in the index)

| Value | Use when querying... |
|---|---|
| `"TEXT_RETRIEVAL"` | A text-only index |
| `"IMAGE_RETRIEVAL"` | An image-only index (images indexed with `detailLevel: "STANDARD_IMAGE"`) |
| `"VIDEO_RETRIEVAL"` | A video-only index, or videos indexed with `embeddingMode: "AUDIO_VIDEO_COMBINED"` |
| `"DOCUMENT_RETRIEVAL"` | A document image index (images indexed with `detailLevel: "DOCUMENT_IMAGE"`) |
| `"AUDIO_RETRIEVAL"` | An audio-only index |
| `"GENERIC_RETRIEVAL"` | A mixed-modality index |

### Other tasks

| Value | Use case |
|---|---|
| `"CLASSIFICATION"` | Embeddings fed into a classifier |
| `"CLUSTERING"` | Embeddings fed into a clustering algorithm |

---

## text object

| Field | Required | Type | Notes |
|---|---|---|---|
| `truncationMode` | Required | string | `"START" \| "END" \| "NONE"`. Docs say `NONE` fails when text exceeds the model's max — **but in practice the API does not enforce this at 8,192 chars** (verified empirically against `us-east-1`). It only fails at the runtime cap below. |
| `value` | Optional* | string | Inline text. **Documented max: 8,192 characters. Runtime enforced max: 50,000 characters** (`expected maxLength: 50000`). The published 8,192 figure is a soft guidance — silent token-level truncation happens above it without `truncationMode: "NONE"` raising. *Either `value` or `source` required. |
| `source` | Optional* | SourceObject | S3 reference to a text file. The `bytes` option of SourceObject is **not** valid for text — only `s3Location`. |
| `segmentationConfig` | Required (segmented only) | object | `maxLengthChars`: int, range 800–50,000, default 32,000 |

---

## image object

| Field | Required | Type | Notes |
|---|---|---|---|
| `format` | Required | string | `"png" \| "jpeg" \| "gif" \| "webp"` (lowercase) |
| `source` | Required | SourceObject | `bytes` (base64) or `s3Location` |
| `detailLevel` | Optional | string | `"STANDARD_IMAGE"` (default, lower res) or `"DOCUMENT_IMAGE"` (higher res, better for text in images) |

**detailLevel guidance:**
- Use `"STANDARD_IMAGE"` for photos, product images, illustrations
- Use `"DOCUMENT_IMAGE"` for PDFs, scanned pages, screenshots with text, receipts, forms
- The `detailLevel` you use at index time determines the correct retrieval purpose: `"IMAGE_RETRIEVAL"` for `STANDARD_IMAGE`, `"DOCUMENT_RETRIEVAL"` for `DOCUMENT_IMAGE`

---

## audio object

| Field | Required | Type | Notes |
|---|---|---|---|
| `format` | Required | string | `"mp3" \| "wav" \| "ogg"` |
| `source` | Required | SourceObject | `bytes` or S3 reference |
| `segmentationConfig` | Required (segmented only) | object | `durationSeconds`: int, range 1–30, default 5 |

**Sync limit:** max audio duration **30 seconds** per call. For longer audio, use the async (segmented) path.

---

## video object

| Field | Required | Type | Notes |
|---|---|---|---|
| `format` | Required | string | `"mp4" \| "mov" \| "mkv" \| "webm" \| "flv" \| "mpeg" \| "mpg" \| "wmv" \| "3gp"` |
| `source` | Required | SourceObject | `bytes` or S3 reference |
| `embeddingMode` | Required | string | `"AUDIO_VIDEO_COMBINED"` (one embedding per segment) or `"AUDIO_VIDEO_SEPARATE"` (two embeddings per segment: one audio, one video) |
| `segmentationConfig` | Required (segmented only) | object | `durationSeconds`: int, range 1–30, default 5 |

**Sync limit:** max video duration **30 seconds** per call. For longer video, use the async path.

---

## SourceObject

```python
# Inline bytes (base64-encoded) — not valid for text inputs
{"bytes": "<base64_string>"}

# S3 reference
{"s3Location": {"uri": "s3://bucket/key"}}
```

---

## Sync response structure (`InvokeModel`)

```python
{
    "embeddings": [
        {
            "embeddingType": "TEXT" | "IMAGE" | "VIDEO" | "AUDIO" | "AUDIO_VIDEO_COMBINED",
            "embedding": [0.123, -0.456, ...],   # float list, length = embeddingDimension
            "truncatedCharLength": 4096           # optional — only present when text was truncated
        }
        # AUDIO_VIDEO_SEPARATE returns two objects (one TEXT/AUDIO, one VIDEO)
    ]
}
```

Parsing for the common single-embedding case:
```python
result = json.loads(response["body"].read())
embedding = result["embeddings"][0]["embedding"]
# Optional: detect silent truncation
if "truncatedCharLength" in result["embeddings"][0]:
    log.warning("Input was truncated at char %s", result["embeddings"][0]["truncatedCharLength"])
```

---

## taskType: SEGMENTED_EMBEDDING (async only)

Used for content longer than the sync limits — long text, audio/video > 30 seconds, or batch jobs.

**Invocation API:** `bedrock_runtime.start_async_invoke(...)` (not `invoke_model_with_response_stream`). Requires:
- `modelId`: `"amazon.nova-2-multimodal-embeddings-v1:0"`
- `outputDataConfig`: `{"s3OutputDataConfig": {"s3Uri": "s3://your-bucket"}}` — async writes results to S3
- `modelInput`: same envelope as sync but with `"taskType": "SEGMENTED_EMBEDDING"` and `segmentedEmbeddingParams`

**Async-only constraint:** async operations only accept S3-backed inputs (per file-limits doc). Image input has no `segmentationConfig` (it's already a single segment); text/audio/video each take a `segmentationConfig`.

`segmentedEmbeddingParams` differs from `singleEmbeddingParams`:
- `text.segmentationConfig.maxLengthChars` — int, 800–50,000, default 32,000
- `audio.segmentationConfig.durationSeconds` — int, 1–30, default 5
- `video.segmentationConfig.durationSeconds` — int, 1–30, default 5

Response: `start_async_invoke` returns `{"invocationArn": "arn:aws:bedrock:...:async-invoke/..."}`. Use `get_async_invoke` to poll status; final results land in S3 as JSONL files (`embedding-text.jsonl`, `embedding-image.jsonl`, etc.) plus a `segmented-embedding-result.json` summary.

Per-segment failure reasons in the async output:
| `failureReason` | Meaning |
|---|---|
| `RAI_VIOLATION_INPUT_TEXT_DEFLECTION` | Input text violates RAI policy |
| `RAI_VIOLATION_INPUT_IMAGE_DEFLECTION` | Input image violates RAI policy |
| `INVALID_CONTENT` | Invalid input |
| `RATE_LIMIT_EXCEEDED` | Throttled |
| `INTERNAL_SERVER_EXCEPTION` | Service-side error |

---

## File size and segment limits

### Sync (`InvokeModel`) input limits

| Source | Limit |
|---|---|
| Inline (any file type, after base64) | 25 MB (≈19 MB raw — base64 inflates ~33%) |
| S3 text | 1 MB; 50,000 characters |
| S3 image | 50 MB |
| S3 video | 30 seconds; 100 MB |
| S3 audio | 30 seconds; 100 MB |

### Async (`StartAsyncInvoke`) input limits — S3 only

| Source | Limit |
|---|---|
| S3 text | 634 MB |
| S3 image | 50 MB |
| S3 video | 2 GB; 2 hours |
| S3 audio | 1 GB; 2 hours |

### Async segment count caps

- Text: max **1900** segments
- Audio/video: max **1434** segments

---

## Region availability

Nova MME is available in a narrow set of regions. As of this writing it ships in `us-east-1`. Other regions where Titan was available (e.g., `us-west-2`, `eu-*`) may not yet be supported. Symptom of using an unsupported region: `ValidationException: The provided model identifier is invalid` — this looks like a model-ID typo but is actually a region availability issue.

Verify availability:
```bash
aws bedrock list-foundation-models --region <region> \
    --query "modelSummaries[?modelId=='amazon.nova-2-multimodal-embeddings-v1:0']"
```
Empty result = not enabled. Cross-check with the [Nova model availability table](https://docs.aws.amazon.com/nova/latest/userguide/multimodal-embedding.html); region coverage expands over time.

---

## Common mistakes

| Mistake | Effect | Fix |
|---|---|---|
| Sending `inputText` instead of `singleEmbeddingParams.text.value` | `ValidationException` | Use the envelope format |
| Sending `embeddingDimension: 512` | `ValidationException` | Use 256, 384, 1024, or 3072 |
| Reading `response["embedding"]` | `None` / `KeyError` | Read `["embeddings"][0]["embedding"]` |
| Using `IMAGE_RETRIEVAL` when index was built with `DOCUMENT_IMAGE` | Poor retrieval quality | Use `DOCUMENT_RETRIEVAL` |
| Using `GENERIC_RETRIEVAL` when index is single-modality | Suboptimal retrieval | Use the modality-specific retrieval value |
| Sending `text` + `image` in same `singleEmbeddingParams` | `ValidationException` | Embed separately and fuse client-side (e.g., mean pool) |
| Calling Nova MME from a region where it isn't enabled | Misleading `ValidationException: The provided model identifier is invalid` | Switch to a supported region (e.g., `us-east-1`) |
| Sending text > 50,000 characters in `text.value` | `ValidationException: expected maxLength: 50000` | Chunk client-side or use the async (`SEGMENTED_EMBEDDING`) path. (Note: docs say 8,192 is the limit; runtime cap is actually 50,000.) |
| Relying on `truncationMode: "NONE"` to surface oversize-text errors | Does not raise at 8,192 chars in practice; silent tokenizer-level truncation occurs | Add a length check upstream if you need to detect truncation deterministically; or check for `truncatedCharLength` in the response |
| Sending `bytes` for `text.source` | `ValidationException` | Use `text.value` for inline, or `s3Location` |
| Capitalized image format (`"JPEG"`, `"PNG"`) | `ValidationException` | Lowercase only: `"jpeg"`, `"png"` |
