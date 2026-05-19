---
name: titan-nova-mme-migration
description: >
  Migrates Python code from Amazon Titan Embeddings models (Titan Text Embedding V2 and Titan
  Multimodal Embeddings G1) to the Amazon Nova Multimodal Embeddings model (Nova MME) on Amazon
  Bedrock. Handles all API differences including the new request schema, dimension mapping,
  client-side text+image fusion workaround, embeddingPurpose optimization, and normalization/binary
  embedding behavior changes.

  Use this skill whenever the user mentions:
  - Migrating from Titan embeddings to Nova embeddings
  - amazon.titan-embed-text-v2, amazon.titan-embed-image-v1, titan-embed, Titan Text V2,
    Titan Multimodal G1, or Titan MME in the context of migration
  - amazon.nova-2-multimodal-embeddings-v1 or Nova MME as a migration target
  - "update my embeddings model", "switch from Titan to Nova", "upgrade embedding model"
  - Any code that calls bedrock.invoke_model with a titan-embed model ID
  Also trigger when the user pastes Titan embedding code and asks how to use Nova instead,
  even if they don't say "migration" explicitly.
---

# Titan → Nova Multimodal Embeddings Migration

## Quick orientation

This skill handles **one source model per migration**. Identify which Titan model the user is on, then follow the matching path:

| Source model | Model ID | Key difference |
|---|---|---|
| Titan Text Embedding V2 | `amazon.titan-embed-text-v2:0` | Text-only; request schema changes |
| Titan Multimodal Embeddings G1 | `amazon.titan-embed-image-v1` | Text+Image; interleaved single-call → separate calls + client-side fusion |

Target model: **`amazon.nova-2-multimodal-embeddings-v1:0`**

---

> **Full API reference:** See `references/nova-mme-api.md` for the complete parameter spec for all modalities (text, image, audio, video), the full `embeddingPurpose` value table, SourceObject schema, segmented embedding, and a common-mistakes table. Read it when you need details beyond what's in this file.

---

## Step 1 — Identify which Titan model is in use

Scan the codebase for `titan-embed-text-v2` or `titan-embed-image-v1` (or any variable holding those model IDs) and pick the matching migration path below. The skill assumes a single source model — if you find both in the same codebase, treat them as two separate migrations and confirm with the user which one to handle first.

---

## Step 2 — Apply the new request schema

### Titan Text V2 → Nova MME

**Old request body:**
```python
body = json.dumps({
    "inputText": text,
    "dimensions": 1024,          # optional
    "normalize": True,           # optional
    "embeddingTypes": ["float"]  # optional, binary also supported
})
response = bedrock.invoke_model(
    body=body,
    modelId="amazon.titan-embed-text-v2:0"
)
embedding = json.loads(response["body"].read())["embedding"]
```

**New request body:**
```python
request_body = {
    "taskType": "SINGLE_EMBEDDING",
    "singleEmbeddingParams": {
        "embeddingDimension": 1024,           # see dimension mapping below
        "embeddingPurpose": "GENERIC_INDEX",  # or GENERIC_RETRIEVAL — see Step 4
        "text": {
            "truncationMode": "END",
            "value": text
        }
    }
}
response = bedrock.invoke_model(
    modelId="amazon.nova-2-multimodal-embeddings-v1:0",
    body=json.dumps(request_body)
)
embedding = json.loads(response["body"].read())["embeddings"][0]["embedding"]
```

Key structural changes:
- Top-level key is `taskType` + `singleEmbeddingParams` (not `inputText`)
- Result lives at `["embeddings"][0]["embedding"]` (not `["embedding"]`)
- `normalize` and `embeddingTypes` are gone — see behavioral notes below

---

### Titan Multimodal G1 → Nova MME (text or image alone)

**Old text-only request:**
```python
body = json.dumps({
    "inputText": text,
    "embeddingConfig": {"outputEmbeddingLength": 1024}
})
```

**New text request** — same as Titan Text V2 migration above.

**Old image-only request:**
```python
body = json.dumps({
    "inputImage": image_bytes_base64,
    "embeddingConfig": {"outputEmbeddingLength": 1024}
})
```

**New image request:**
```python
request_body = {
    "taskType": "SINGLE_EMBEDDING",
    "singleEmbeddingParams": {
        "embeddingPurpose": "GENERIC_INDEX",
        "embeddingDimension": 1024,
        "image": {
            "format": "jpeg",          # or "png", "gif", "webp"
            "detailLevel": "STANDARD_IMAGE",
            "source": {"bytes": image_bytes_base64}
        }
    }
}
response = bedrock.invoke_model(
    modelId="amazon.nova-2-multimodal-embeddings-v1:0",
    body=json.dumps(request_body)
)
embedding = json.loads(response["body"].read())["embeddings"][0]["embedding"]
```

---

### Titan Multimodal G1 → Nova MME (combined text+image — client-side fusion)

Titan G1 could produce a single fused embedding from text+image in one API call. **Nova MME does not support this.** Instead, embed each modality separately and average (mean pooling):

```python
def generate_text_embedding(bedrock_client, text, dim=1024, purpose="GENERIC_INDEX"):
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingDimension": dim,
            "embeddingPurpose": purpose,
            "text": {"truncationMode": "END", "value": text}
        }
    }
    response = bedrock_client.invoke_model(
        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
        body=json.dumps(request_body)
    )
    return json.loads(response["body"].read())["embeddings"][0]["embedding"]


def generate_image_embedding(bedrock_client, image_bytes_base64, dim=1024,
                              fmt="jpeg", purpose="GENERIC_INDEX"):
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": purpose,
            "embeddingDimension": dim,
            "image": {
                "format": fmt,
                "detailLevel": "STANDARD_IMAGE",
                "source": {"bytes": image_bytes_base64}
            }
        }
    }
    response = bedrock_client.invoke_model(
        modelId="amazon.nova-2-multimodal-embeddings-v1:0",
        body=json.dumps(request_body)
    )
    return json.loads(response["body"].read())["embeddings"][0]["embedding"]


def generate_fused_embedding(bedrock_client, text, image_bytes_base64, dim=1024,
                              purpose="GENERIC_INDEX"):
    """Mean-pool text and image embeddings as a Nova MME replacement for Titan G1's
    native text+image fusion."""
    text_emb = generate_text_embedding(bedrock_client, text, dim, purpose)
    img_emb = generate_image_embedding(bedrock_client, image_bytes_base64, dim,
                                        purpose=purpose)
    return [(t + i) / 2 for t, i in zip(text_emb, img_emb)]
```

At index time: `purpose="GENERIC_INDEX"`. At query time: use the modality-specific retrieval value — see Step 4 for the full decision tree.

---

## Step 3 — Map dimensions

Nova MME supports: **3072, 1024, 384, 256**. Titan Text V2 supports 1024, 512, 256.

| Old dimension | Recommended Nova dimension |
|---|---|
| 256 | 256 |
| 384 | 384 |
| 512 | **384 or 1024** — 512 is not available; pick based on latency/accuracy tradeoff |
| 1024 | 1024 |

If the user's code hard-codes `512`, flag it and ask which target dimension to use (384 for smaller/faster, 1024 for higher accuracy). Update `embeddingDimension` accordingly.

Note: if migrating an existing vector index, changing dimensions requires rebuilding the entire index, since vector dimensions must be consistent. Warn the user about this if dimension changes.

---

## Step 4 — Set embeddingPurpose correctly at every call site

`embeddingPurpose` is a Nova MME-only parameter that Titan never had. It tells the model how the embedding will be used, allowing it to apply purpose-specific optimizations. **Choosing the wrong value degrades retrieval quality.** Read the call site carefully and apply the decision tree below.

### The full set of allowed values

**For indexing (building the corpus / vector store):**

| Value | When to use |
|---|---|
| `"GENERIC_INDEX"` | Indexing content of **any** modality — text, images, video, audio, documents. Use this whenever you are building the index, regardless of what you're indexing. |

**For retrieval (embedding a query at search time):**

| Value | When to use |
|---|---|
| `"TEXT_RETRIEVAL"` | Query against a **text-only** index |
| `"IMAGE_RETRIEVAL"` | Query against an **image-only** index (images embedded with `detailLevel: "STANDARD_IMAGE"`) |
| `"VIDEO_RETRIEVAL"` | Query against a **video-only** index |
| `"DOCUMENT_RETRIEVAL"` | Query against a **document image** index (images embedded with `detailLevel: "DOCUMENT_IMAGE"`) |
| `"AUDIO_RETRIEVAL"` | Query against an **audio-only** index |
| `"GENERIC_RETRIEVAL"` | Query against a **mixed-modality** index (multiple content types in the same vector store) |

**For non-retrieval tasks:**

| Value | When to use |
|---|---|
| `"CLASSIFICATION"` | Embeddings that will be fed to a classifier |
| `"CLUSTERING"` | Embeddings that will be used for clustering algorithms |

### Decision logic — how to pick the right value at each call site

**Step A: Is this call building an index or querying one?**

- Building (batch-processing a corpus, preprocessing data) → always `"GENERIC_INDEX"`, regardless of modality
- Querying (runtime, user search, similarity lookup) → go to Step B

**Step B (query calls only): What modality is in the index being searched?**

- Index contains only text embeddings → `"TEXT_RETRIEVAL"`
- Index contains only standard images → `"IMAGE_RETRIEVAL"`
- Index contains only document images (PDFs, scans, high-res text images) → `"DOCUMENT_RETRIEVAL"`
- Index contains only video embeddings → `"VIDEO_RETRIEVAL"`
- Index contains only audio embeddings → `"AUDIO_RETRIEVAL"`
- Index contains a mix of modalities → `"GENERIC_RETRIEVAL"`
- The query itself is the content (no retrieval — just comparing embeddings) → `"GENERIC_INDEX"`

**Step C: Non-retrieval tasks**

- Feeding into a classification model → `"CLASSIFICATION"`
- Feeding into a clustering algorithm (k-means, DBSCAN, etc.) → `"CLUSTERING"`

### Common patterns and examples

**Text RAG (most common migration case):**
```python
# Index time — embedding documents
{"embeddingPurpose": "GENERIC_INDEX", "text": {"value": document_text}}

# Query time — embedding user query
{"embeddingPurpose": "TEXT_RETRIEVAL", "text": {"value": user_query}}
```

**Image search app (users search images with text queries):**
```python
# Index time — embedding product images
{"embeddingPurpose": "GENERIC_INDEX", "image": {"format": "jpeg", ...}}

# Query time — embedding text query to find images
{"embeddingPurpose": "IMAGE_RETRIEVAL", "text": {"value": search_query}}
```

**Document search (PDFs, scanned pages):**
```python
# Index time — embedding document pages at high resolution
{"embeddingPurpose": "GENERIC_INDEX", "image": {"format": "jpeg", "detailLevel": "DOCUMENT_IMAGE", ...}}

# Query time — embedding text query to find documents
{"embeddingPurpose": "DOCUMENT_RETRIEVAL", "text": {"value": search_query}}
```

**Mixed-modality index (text + images in the same vector store):**
```python
# Index time — same for both modalities
{"embeddingPurpose": "GENERIC_INDEX", "text": {...}}
{"embeddingPurpose": "GENERIC_INDEX", "image": {...}}

# Query time — GENERIC because the index is mixed
{"embeddingPurpose": "GENERIC_RETRIEVAL", "text": {"value": user_query}}
```

**When migrating from Titan (which had no embeddingPurpose):**
If the existing Titan code doesn't distinguish index vs. query calls, infer from context:
- Functions with names like `embed_document`, `index_item`, `process_batch` → `GENERIC_INDEX`
- Functions with names like `embed_query`, `search`, `get_query_vector` → use the appropriate `*_RETRIEVAL` value based on what the index contains
- Ambiguous utility functions called in both contexts → add a `purpose` parameter and let callers pass the right value

---

## Step 5 — Handle behavior changes (warn the user)

### Normalization (from Titan Text V2 only)

Titan Text V2 had an explicit `normalize` parameter (default `True`). Nova MME always returns normalized embeddings — there's no way to disable this. If the user's code set `normalize=False`, warn them:

> ⚠️ Nova MME always returns normalized embeddings. If your downstream code assumed non-normalized vectors (e.g., computing raw dot products as distance scores), you may need to adjust it. For cosine similarity, normalized embeddings are already ideal — no change needed.

### Binary embeddings (from Titan Text V2 only)

Titan Text V2 supported `embeddingTypes: ["binary"]` for compact storage. Nova MME returns only float32 embeddings. If the user's code used binary embeddings, warn them:

> ⚠️ Nova MME does not natively produce binary embeddings. To reproduce binary quantization, apply client-side thresholding after receiving the float embedding:
> ```python
> binary_embedding = [1 if x > 0 else 0 for x in float_embedding]
> ```
> This won't perfectly replicate Titan's internal quantization, so re-benchmarking retrieval quality is recommended.

### Text input limit change (from Titan Multimodal G1 only)

Titan G1 had a 256-token text limit. Nova MME's published schema documents `text.value` as max 8,192 characters, but the runtime API actually enforces `maxLength: 50000` characters and silently truncates inputs whose **tokenized** form exceeds the model's internal context window — `truncationMode: "NONE"` does **not** fail at 8,192 chars in practice. Treat the published 8,192 figure as a soft target, not a hard cap.

Practical guidance:
- Truncation logic added to work around Titan G1's 256-token limit is usually unnecessary now — safe to leave in place.
- For inputs over ~8,000 characters, prefer `truncationMode: "END"` (or `"START"`) so the model can silently truncate. Don't rely on `"NONE"` to surface oversize-text errors at the documented threshold; it won't.
- Inputs over **50,000 characters** are hard-rejected with `ValidationException: expected maxLength: 50000`. For longer text, chunk client-side or use the async (`SEGMENTED_EMBEDDING`) path with `text.segmentationConfig.maxLengthChars`.

### Response field additions (informational)

Nova MME responses include two fields Titan never returned:
- `embeddings[0].embeddingType` — one of `"TEXT" | "IMAGE" | "VIDEO" | "AUDIO" | "AUDIO_VIDEO_COMBINED"`. Always present. Useful when the index could mix modalities; otherwise ignorable.
- `embeddings[0].truncatedCharLength` — only returned when the **tokenized** input was truncated; not triggered just by exceeding 8,192 chars. Treat its presence as a signal to log/alert and consider chunking input upstream.

---

## Step 6 — Update model IDs everywhere

Search the codebase for all occurrences of the old model ID strings and replace them:

```
amazon.titan-embed-text-v2:0   →  amazon.nova-2-multimodal-embeddings-v1:0
amazon.titan-embed-image-v1    →  amazon.nova-2-multimodal-embeddings-v1:0
amazon.titan-embed-image-v1:0  →  amazon.nova-2-multimodal-embeddings-v1:0
```

Also check: config files, environment variables, CDK/CloudFormation templates, README docs.

### Region availability — verify before shipping

Nova MME has narrower regional availability than the Titan models. The Titan model IDs may have worked in `us-west-2`, `eu-*`, or `ap-*`; Nova MME does **not** ship in all of those (yet).

When migrating, look at every place a region is set — `boto3.client("bedrock-runtime", region_name=...)`, `AWS_REGION` env var, deployment configs, IaC templates — and flag any region that isn't currently a Nova MME region. The symptom of an unavailable region is a misleading `ValidationException: The provided model identifier is invalid` (it's actually a region issue, not a model-ID issue).

Verify availability for the user's region before declaring the migration done:
```bash
aws bedrock list-foundation-models --region <region> \
    --query "modelSummaries[?modelId=='amazon.nova-2-multimodal-embeddings-v1:0']"
```
An empty result means Nova MME isn't enabled in that region. Tell the user to switch to a supported region (e.g., `us-east-1`) or wait for availability before deploying. Always confirm against the latest [Nova model availability table](https://docs.aws.amazon.com/nova/latest/userguide/multimodal-embedding.html) — regions expand over time.

---

## Step 7 — Explain every change to the user

Always deliver two things: the working migrated code **and** a clear written explanation. The explanation is not optional — it helps the user understand what broke, why, and what you changed so they can maintain the code going forward.

Structure your explanation like this:

### What changed and why

For each change made, write a short section with:
- **What was changed** (the specific code, parameter, or pattern)
- **Why it had to change** (the API difference that forced it)
- **What the new code does** (what the replacement achieves)

Always cover these specific areas when they apply:

**1. Model ID**
> Changed `amazon.titan-embed-text-v2:0` → `amazon.nova-2-multimodal-embeddings-v1:0`. This is the model identifier Bedrock uses to route your request. The Titan models are separate products; Nova MME is a new unified model that handles text, image, document, video, and audio.

**2. Request schema**
> Titan used a flat JSON body (`inputText`, `inputImage`, `dimensions`). Nova MME uses a structured envelope: `taskType: "SINGLE_EMBEDDING"` wrapping a `singleEmbeddingParams` object. This is a complete format change — the old keys are not recognized by Nova MME and will cause a validation error if sent.

**3. Response parsing**
> Titan returned `{"embedding": [...]}` at the top level. Nova MME returns `{"embeddings": [{"embedding": [...]}]}` — a list even for single inputs. Your code must now index `["embeddings"][0]["embedding"]` instead of `["embedding"]`.

**4. New `embeddingPurpose` parameter**
> Nova MME introduces `embeddingPurpose`, which Titan never had. It tells the model how the embedding will be used so it can optimize the vector space accordingly. There are 9 possible values — the key rule is:
>
> - **All indexing calls** (building the corpus): always `"GENERIC_INDEX"`, regardless of modality
> - **Query calls** (searching at runtime): pick the value that matches what's in the index:
>   - Text-only index → `"TEXT_RETRIEVAL"`
>   - Image-only index (`STANDARD_IMAGE`) → `"IMAGE_RETRIEVAL"`
>   - Document image index (`DOCUMENT_IMAGE`) → `"DOCUMENT_RETRIEVAL"`
>   - Video-only index → `"VIDEO_RETRIEVAL"`
>   - Audio-only index → `"AUDIO_RETRIEVAL"`
>   - Mixed-modality index → `"GENERIC_RETRIEVAL"`
> - **Classification tasks** → `"CLASSIFICATION"`
> - **Clustering tasks** → `"CLUSTERING"`
>
> In this migration, [describe what was set and why based on the actual code].

**5. Dimension mapping** (only if dimension changed)
> Nova MME supports 256, 384, 1024, and 3072. It does **not** support 512 — attempting to use 512 raises a `ValidationException`. Changed `512` → `384` (or `1024` per user preference). If you have an existing vector index, you must **rebuild it entirely** because old and new embeddings are in incompatible vector spaces.

**6. Text+image fusion workaround** (only for Titan G1 migrations)
> Titan Multimodal G1 accepted `inputText` and `inputImage` together in a single API call and returned one pre-fused embedding. Nova MME does not support this — each modality must be embedded in a separate call. To preserve equivalent behavior, the migrated code now calls Nova MME twice (once for text, once for image) and averages the results element-wise (mean pooling: `(text_emb[i] + image_emb[i]) / 2`). This adds one extra API call per item but achieves semantically equivalent fusion.

**7. Normalization** (only if `normalize=False` was present)
> Titan Text V2 had a `normalize` parameter you set to `False`. Nova MME always returns L2-normalized (unit-length) embeddings — this cannot be disabled. Removed the `normalize` key (Nova MME doesn't accept it). If any downstream code relied on unnormalized vector magnitudes for scoring, it may need adjustment. For cosine similarity, normalized vectors are already correct and no downstream changes are needed.

**8. Binary embeddings** (only if `embeddingTypes: ["binary"]` was present)
> The `embeddingTypes` parameter was specific to Titan Text V2. Nova MME always returns float32 and does not accept this parameter. Removed it from the request. If you need compact binary vectors, apply client-side thresholding: `[1 if x > 0 else 0 for x in embedding]`.

### Format

End your response with the full migrated code, clearly labeled. The explanation comes first so the user understands what they're looking at before they see the code.

---

## Internal delivery checklist (verify before responding)

- [ ] All Titan model IDs replaced with `amazon.nova-2-multimodal-embeddings-v1:0`
- [ ] Request schema updated (`taskType` / `singleEmbeddingParams` structure)
- [ ] Response parsing updated (`["embeddings"][0]["embedding"]`)
- [ ] `embeddingPurpose` set at each call site
- [ ] Dimension 512 replaced (if present)
- [ ] Combined text+image calls replaced with mean-pooling fusion (if G1 was the source)
- [ ] User warned about normalization change if they used `normalize=False`
- [ ] User warned about binary embeddings if they used `embeddingTypes: ["binary"]`
- [ ] User reminded to rebuild vector index if dimensions changed
- [ ] Explanation written covering every change that was made
