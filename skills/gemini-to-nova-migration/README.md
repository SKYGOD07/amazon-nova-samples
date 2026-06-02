# Gemini → Nova 2 Lite Migration Skill

An [Agent Skill](https://agentskills.io/specification) that migrates Google Gemini Python code and prompts to [Amazon Nova 2 Lite](https://docs.aws.amazon.com/nova/latest/userguide/) (`us.amazon.nova-2-lite-v1:0`) on Amazon Bedrock.

The skill converts SDK calls (`google-genai` / `google-generativeai` → `boto3` Bedrock Runtime `converse`) and rewrites prompts to follow Nova 2 Lite formatting and constraints. Every migration delivers two things: **working migrated code** and an **explanation of every change**, including any features that can't be ported 1:1.

The skill supports **Gemini 2.0 / 2.5 / 3.x** as source models, across three API styles:

| Source API style | Detected from |
|---|---|
| Deprecated SDK | `import google.generativeai as genai` — `GenerativeModel`, `generate_content` |
| Current SDK (`generateContent`) | `from google import genai` — `client.models.generate_content` |
| Current SDK (Interactions API) | `from google import genai` — `client.interactions.create` |

**Target:** `us.amazon.nova-2-lite-v1:0` (Nova Pro / Premier suggested for `gemini-2.5-pro` and `gemini-3.1-pro-preview` source code)

## Skill structure

```
gemini-to-nova-migration/
├── SKILL.md                              # Skill instructions and migration workflow
├── README.md                             # This file
└── references/
    ├── feature-mapping.md                # Complete Gemini → Nova mapping tables
    ├── code-examples.md                  # Before/after code patterns
    └── generate-content-patterns.md      # generateContent, Interactions API + deprecated SDK specifics
```

## What the skill handles

| Area | Detail |
|---|---|
| SDK | `google-genai` / `google-generativeai` → `boto3` bedrock-runtime `converse` / `converse_stream` |
| Prompt format | XML tags / free-form → `##Section Name##` delimiters with canonical Nova section names |
| System instructions | `system_instruction=` → `system=[{"text": ...}]`, re-specified per call |
| Multimodal | Enforces system-prompt-is-persona-only rule and media-before-text content ordering |
| Function calling | `function_declarations` (OpenAPI) → `toolSpec` (JSON Schema), `tool_config.mode` → `toolChoice` |
| Structured output | `response_mime_type` + `response_schema` → inline schema (simple) or tool-forcing (complex) |
| Reasoning / thinking | `thinking_config` → `additionalModelRequestFields.reasoningConfig`, mapped to a Nova effort level |
| Stateful turns | `previous_interaction_id` / `store=true` → full message history passed each call |
| Inference config | Picks temperature / top-p / reasoning per the Nova use-case tables |

## API differences at a glance

| | Gemini | Nova 2 Lite |
|---|---|---|
| **SDK** | `google-genai` | `boto3` bedrock-runtime |
| **Call** | `client.models.generate_content()` / `client.interactions.create()` | `client.converse()` |
| **Auth** | `GOOGLE_API_KEY` | AWS credentials (IAM role, profile, env vars) |
| **System prompt** | `system_instruction=` (full instructions, all modalities) | `system=[{"text": ...}]` (persona only for multimodal) |
| **Tools** | `function_declarations` (OpenAPI schema) | `toolSpec` (JSON Schema) |
| **Tool mode** | `tool_config.mode` (`AUTO`/`ANY`/`NONE`) | `toolChoice` (`auto`/`any`/`tool`) |
| **Structured output** | `response_mime_type` + `response_schema` | Inline prompt schema or tool-forcing |
| **Reasoning** | `thinking_config=ThinkingConfig(...)` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| **Streaming** | `generate_content_stream()` | `converse_stream()` |
| **Stateful turns** | `previous_interaction_id`, `store=true` | Pass full message history each call |
| **Media ordering** | Any order | Media MUST precede text |

## Reasoning effort mapping

When the source model supports thinking **and** it's enabled, the skill asks the user which Nova effort level to use:

| Nova effort | Config |
|---|---|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` — must omit `inferenceConfig` |

If the source model has no native thinking (e.g. `gemini-2.0-flash`), or thinking isn't enabled, omit `additionalModelRequestFields` entirely (reasoning is disabled by default).

## Installation

### Claude Code

This skill ships as the `gemini-to-nova-migration` plugin via the `aws-samples-amazon-nova-samples` marketplace.

Add the marketplace, then install the plugin:

```
/plugin marketplace add https://github.com/aws-samples/amazon-nova-samples
/plugin install gemini-to-nova-migration@aws-samples-amazon-nova-samples
```

After install, invoke the skill on your Gemini code with `/gemini-to-nova`.

## Prerequisites

- An AWS account with Amazon Bedrock access
- `us.amazon.nova-2-lite-v1:0` enabled in your region
- Python 3.8+ with `boto3` (only needed to run the migrated code)

AWS credentials and Bedrock access are only required when you actually run the migrated code — the migration itself runs inside the host tool.

## Example prompts

```
Migrate this Gemini code to Amazon Nova 2 Lite:
<paste your google-genai code>
```

```
I have a Gemini 2.5 Flash function-calling app with thinking enabled.
Convert it to Nova 2 Lite.
```

```
Rewrite this Gemini multimodal prompt (image input) for Nova 2 Lite.
```

## Related resources

- [Amazon Nova User Guide](https://docs.aws.amazon.com/nova/latest/userguide/)
- [Amazon Bedrock `converse` API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Agent Skills open standard — Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Amazon Nova Samples](https://github.com/aws-samples/amazon-nova-samples)
