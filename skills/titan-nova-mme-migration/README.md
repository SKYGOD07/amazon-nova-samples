# Titan → Nova Multimodal Embeddings Migration Skill

An [Agent Skill](https://agentskills.io/specification) that migrates Amazon Bedrock embedding code from the Titan family of models to [Amazon Nova Multimodal Embeddings](https://docs.aws.amazon.com/nova/latest/userguide/nova-multimodal-embeddings.html) (`amazon.nova-2-multimodal-embeddings-v1:0`).

The skill handles all API differences and delivers two things for every migration: **working migrated code** and a **plain-language explanation** of every change.

The skill supports **one source model per migration** — pick whichever path matches the user's existing code:

| Migration path | Source model ID |
|---|---|
| Titan Text Embedding V2 → Nova MME | `amazon.titan-embed-text-v2:0` |
| Titan Multimodal Embeddings G1 → Nova MME | `amazon.titan-embed-image-v1` / `amazon.titan-embed-image-v1:0` |

**Target:** `amazon.nova-2-multimodal-embeddings-v1:0`

## Skill structure

```
titan-nova-mme-migration/
├── SKILL.md                          # Skill instructions
├── README.md                         # This file
├── references/
│   └── nova-mme-api.md               # Complete Nova MME parameter reference
├── .claude-plugin/plugin.json        # Claude Code plugin manifest
├── .codex-plugin/plugin.json         # Cursor plugin manifest
└── .mcp.json                         # MCP server config (aws-mcp)
```

## What the skill handles

| Area | Detail |
|---|---|
| Request schema | Titan's flat body → `taskType + singleEmbeddingParams` envelope |
| Response parsing | `["embedding"]` → `["embeddings"][0]["embedding"]` |
| `embeddingPurpose` | All 9 values with a decision tree: `GENERIC_INDEX` for all indexing, modality-specific `*_RETRIEVAL` for queries |
| Dimension mapping | 512 not supported → 384 or 1024; warns about index rebuild |
| Text+image fusion | Titan G1 single-call → two separate calls + mean pooling |
| Normalization | `normalize=False` removed; always-normalized behavior explained |
| Binary embeddings | `embeddingTypes` removed; client-side thresholding workaround provided |

## API differences at a glance

| | Titan Text V2 | Titan Multimodal G1 | Nova MME |
|---|---|---|---|
| **Model ID** | `amazon.titan-embed-text-v2:0` | `amazon.titan-embed-image-v1` | `amazon.nova-2-multimodal-embeddings-v1:0` |
| **Modalities** | Text | Text, Image | Text, Image, Document, Video, Audio |
| **Request schema** | Flat JSON | Flat JSON | `taskType + singleEmbeddingParams` |
| **Response path** | `["embedding"]` | `["embedding"]` | `["embeddings"][0]["embedding"]` |
| **Supported dimensions** | 1024, 512, 256 | 1024, 384, 256 | 3072, 1024, 384, 256 |
| **Max text input** | 8,192 tokens | 256 tokens | 8,192 chars (docs); 50,000 chars (runtime cap) |
| **`embeddingPurpose`** | Not supported | Not supported | Required — 9 values |
| **Text+Image in one call** | N/A | Yes | No — separate calls + client-side fusion |
| **Normalization control** | `normalize` param | Always on | Always on, no param |
| **Binary embeddings** | `embeddingTypes: ["binary"]` | No | Client-side thresholding |

## `embeddingPurpose` quick reference

The key rule: **all indexing calls use `GENERIC_INDEX`**. At query time, match to what's in the index:

| Index content | Query purpose |
|---|---|
| Text only | `TEXT_RETRIEVAL` |
| Standard images (`STANDARD_IMAGE`) | `IMAGE_RETRIEVAL` |
| Document images (`DOCUMENT_IMAGE`) | `DOCUMENT_RETRIEVAL` |
| Video | `VIDEO_RETRIEVAL` |
| Audio | `AUDIO_RETRIEVAL` |
| Mixed modalities | `GENERIC_RETRIEVAL` |
| Classification task | `CLASSIFICATION` |
| Clustering task | `CLUSTERING` |

See [`references/nova-mme-api.md`](references/nova-mme-api.md) for the complete parameter specification.

## Installation

### Claude Code

Add the `aws-samples/amazon-nova-samples` marketplace, then install the plugin:

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install titan-nova-mme-migration@aws-samples-amazon-nova-samples
```

## Prerequisites

- An AWS account with Amazon Bedrock access
- `amazon.nova-2-multimodal-embeddings-v1:0` enabled in your region
- Python 3.8+ with `boto3`

## Example prompts

```
Migrate my Titan Text V2 embedding code to Nova MME.
```

```
I'm using amazon.titan-embed-image-v1 for product image search — my embed_text_and_image
function sends text and image in one call. How do I migrate to Nova?
```

```
We have a RAG pipeline using Titan Text V2 with dimension 512.
Migrate it to Nova MME — we're fine rebuilding the index.
```

## Related resources

- [Amazon Nova Multimodal Embeddings — User Guide](https://docs.aws.amazon.com/nova/latest/userguide/nova-multimodal-embeddings.html)
- [Amazon Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/)
- [Agent Skills open standard — Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Amazon Nova Samples](https://github.com/aws-samples/amazon-nova-samples)

## License

This project is licensed under the Apache 2.0 License.
