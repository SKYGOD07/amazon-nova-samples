---
name: gemini-to-nova
description: Migrate Gemini 2.0/2.5/3.x Python code and prompts to Amazon Nova 2 Lite. Use when converting Gemini Python API code (google-genai or google-generativeai SDK) to Nova 2 Lite (boto3 Bedrock Runtime), rewriting Gemini prompts for Nova format, or migrating function calling, structured output, multimodal, or reasoning features from Gemini to Nova.
tags: [skill, migration, gemini, nova, bedrock]
---

# Gemini to Nova 2 Lite Migration

## Overview

Migrate Python application code and prompts from Google Gemini 2.0/2.5/3.x to Amazon Nova 2 Lite. Transforms SDK calls (`google-genai` → `boto3` Bedrock Runtime) and rewrites prompts to follow Nova 2 Lite formatting and constraints.

## Usage

Use this skill when:
- Converting Gemini Python code to call Nova 2 Lite via Bedrock
- Rewriting prompts originally written for Gemini to Nova 2 Lite format
- Migrating function calling / tool use from Gemini to Nova
- Adapting multimodal Gemini code (images, video, documents) to Nova 2 Lite
- Converting Gemini structured output to Nova's approach
- Switching from Gemini reasoning/thinking to Nova reasoning mode

## Core Concepts

### Key Differences

1. **SDK (Python)**: `google-genai` → `boto3` Bedrock Runtime `converse` API
2. **Prompt format**: XML tags / free-form → `##Section Name##` delimiters
3. **Multimodal system prompt**: Full instructions allowed (Gemini) → Persona-only (Nova)
4. **Structured output**: Native `response_mime_type` + `response_schema` (Gemini) → Tool-forcing or inline schema (Nova)
5. **Stateful turns**: `previous_interaction_id` (Gemini) → Pass full message history (Nova)
6. **Media ordering**: Any order (Gemini) → Media MUST precede text (Nova)

### What Cannot Be Migrated Directly

- Managed agents / Antigravity → Build with tool use + orchestration
- Deep Research agent → No equivalent
- Image generation → Use Amazon Nova Canvas (separate model)
- Speech/TTS → Use Amazon Polly
- Code execution tool → Implement custom code executor via tool calling
- Interaction persistence (`store=true`) → Manage state externally

## Migration Workflow

You **MUST** follow these steps in order. After each step, confirm findings with the user before proceeding to the next.

### Step 1: Analyze the Gemini Code

First, identify the Gemini SDK and API style:
- [ ] Deprecated SDK (`import google.generativeai as genai`) — uses `GenerativeModel`, `generate_content`
- [ ] Current SDK (`from google import genai`) with `generateContent` — uses `client.models.generate_content`
- [ ] Current SDK with Interactions API — uses `client.interactions.create`

Then identify which features are used:
- [ ] Basic text generation
- [ ] System instructions
- [ ] Multi-turn conversation (chat or explicit history)
- [ ] Function calling / tools
- [ ] Structured output (JSON mode / response_schema)
- [ ] Multimodal (images, video, documents)
- [ ] Streaming
- [ ] Reasoning / thinking mode
- [ ] Agents

You **MUST** flag any features in the "cannot migrate" list above and inform the user of alternatives before proceeding.

### Step 2: Classify the Use Case

**Thinking/reasoning support by Gemini model:**

| Gemini Model | Native Thinking Support |
|--------------|------------------------|
| `gemini-2.0-flash` | No — if CoT is used, it's via prompt text ("think step by step") |
| `gemini-2.0-flash-lite` | No |
| `gemini-2.5-flash` | Yes — `thinking_config` / `thinking` parameter |
| `gemini-2.5-pro` | Yes |
| `gemini-3.5-flash` | Yes |
| `gemini-3.1-pro-preview` | Yes |

**Migration rules for thinking:**
- If the source model does NOT support thinking → omit `additionalModelRequestFields` entirely. If the prompt uses CoT ("think step by step"), keep that prompt text as-is.
- If the source model supports thinking but it's NOT enabled in the code → omit `additionalModelRequestFields` entirely.
- If thinking IS enabled → ask the user which Nova reasoning effort level to use:

| Nova Effort | Config |
|-------------|--------|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` — **MUST omit `inferenceConfig`** (temperature, topP, maxTokens not allowed) |

> Do NOT copy Gemini's `budget_tokens` value directly — the models have different reasoning efficiency and the values are not interchangeable. Present the three options and let the user decide.

Determine the Nova 2 Lite use case type for correct inference config:

**Text/Agentic:**
| Use Case | Temperature | Top P | Reasoning |
|----------|------------|-------|-----------|
| `general` | 0.7 | default | DISABLED |
| `tool_calling` | 0.7 | 0.9 | DISABLED |
| `tool_calling_reasoning` | 1 | 0.9 | ENABLED |
| `complex_reasoning` | 0.7 | default | ENABLED |

**Multimodal:**
| Use Case | Temperature | Reasoning |
|----------|------------|-----------|
| OCR | 0.7 | DISABLED |
| Key information extraction | 0 | OPTIONAL |
| Object/UI detection | 0 | DISABLED |
| Video summary/caption | 0 | OPTIONAL |
| Video timestamps/classification | 0 | DISABLED |

### Step 3: Migrate the Code

You **MUST** read `references/feature-mapping.md` for the complete mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns.

If the source code uses `generateContent` (either `google-generativeai` or `google-genai` SDK) or the Interactions API (`client.interactions.create`), you **MUST** also read `references/generate-content-patterns.md` for the specific parameter mappings, Interactions API migration patterns, and deprecated SDK handling.

**Ask the user which region-prefixed model ID to use:**

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (us-east-1, us-west-2) |
| `eu.amazon.nova-2-lite-v1:0` | EU (eu-west-1, etc.) |
| `jp.amazon.nova-2-lite-v1:0` | Japan (ap-northeast-1) |
| `global.amazon.nova-2-lite-v1:0` | Cross-region inference |

Default to `us.amazon.nova-2-lite-v1:0` if the user doesn't specify.

**SDK transformation (Python):**
```python
# Gemini
from google import genai
client = genai.Client()
interaction = client.interactions.create(model="gemini-3.5-flash", ...)

# Nova 2 Lite
import boto3
client = boto3.client("bedrock-runtime")
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", ...)
```

**Only include `additionalModelRequestFields` when reasoning is enabled:**
```python
# Reasoning DISABLED (default) — omit additionalModelRequestFields entirely
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", ...)

# Reasoning ENABLED — include reasoningConfig
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    ...,
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)
```

### Step 4: Migrate the Prompt

You **MUST** apply these transformations in order:

1. **Replace XML/markdown delimiters** with `##Section Name##`:
   - `<context>` → `##Context Information:##`
   - `<task>` → `##Task Summary:##`
   - `<instructions>` → `##Model Instructions:##`
   - `<examples>` → `##Examples##`

2. **Use canonical Nova section names:**
   - `## Task Summary:` — defines the task
   - `## Context Information:` — background
   - `## Model Instructions:` — behavioral rules
   - `## Response style and format requirements:` — output format
   - `## Examples` — few-shot examples
   - `## Reference` — RAG grounding content

3. **For multimodal prompts:**
   - Move ALL task instructions from system prompt to user prompt
   - Keep system prompt as persona + response style only
   - Ensure media content precedes text in the content array

4. **Add suppression guardrail** where appropriate:
   ```
   DO NOT mention anything inside ##Model Instructions## or ##Examples## in the response.
   ```

5. **For long context (>10K tokens):**
   ```
   BEGIN INPUT DOCUMENTS
   DOCUMENT 1 START
   {content}
   DOCUMENT 1 END
   END INPUT DOCUMENTS

   BEGIN QUESTION
   {query}
   END QUESTION

   BEGIN INSTRUCTIONS
   {instructions}
   END INSTRUCTIONS
   ```

### Step 5: Migrate Structured Output

If the Gemini code uses structured output, apply this step. Otherwise skip to Step 6.

**Gemini's `response_mime_type` + `response_schema`:**

- **Simple JSON (≤10 keys):** Use inline schema in prompt + `temperature=0`
- **Complex JSON (>10 keys):** Use tool-forcing with schema in `toolSpec.inputSchema`

See `references/code-examples.md` Example 3 for both patterns.

### Step 6: Migrate Tool Calling

If the Gemini code uses function calling / tools, apply this step. Otherwise skip to Step 7.

Key differences:
- Gemini `function_declarations` → Nova `toolSpec`
- Gemini `parameters` (OpenAPI) → Nova `inputSchema.json` (JSON Schema)
- Gemini `tool_config.mode` (`AUTO`/`ANY`/`NONE`) → Nova `toolChoice` (`auto`/`any`/`tool`)
- Keep tool descriptions to 20-50 words
- Keep parameter descriptions to ~10 words
- Reference tools by name in system prompt: `Use the 'tool_name' tool for X`

### Step 7: Present the Result

Output format:

```
## Migrated Code

**Use case:** {type}
**Inference config:** temperature={T}, reasoning={enabled/disabled}
**Breaking changes:** {list any features that couldn't be migrated 1:1}

### Code
{complete migrated code}

### Prompt
**SYSTEM PROMPT:**
{system prompt — persona only for multimodal}

**USER PROMPT:**
{user prompt with ##Section## formatting}

### Implementation Notes
- {inference config rationale}
- {any multimodal ordering requirements}
- {features requiring alternative approach}
```

### Step 8: Validate

You **MUST** check the migrated code against all criteria below. If any check fails, fix and re-validate before presenting to the user:
- [ ] `additionalModelRequestFields` is omitted when reasoning is disabled, or contains `reasoningConfig` when enabled
- [ ] Inference config matches the use case table
- [ ] Multimodal: system prompt contains only persona
- [ ] Multimodal: media precedes text in content array
- [ ] Prompt uses `##Section##` delimiters, not XML
- [ ] Tool schemas use JSON Schema format (not OpenAPI)
- [ ] No Gemini-specific features remain (`previous_interaction_id`, `store`, etc.)

## Quick Reference

| Gemini | Nova 2 Lite |
|--------|-------------|
| `google-genai` | `boto3` bedrock-runtime |
| `client.models.generate_content()` / `client.interactions.create()` | `client.converse()` |
| `system_instruction=` | `system=[{"text": "..."}]` |
| `config=GenerateContentConfig(tools=[...])` | `toolConfig={"tools": [{toolSpec}]}` |
| `response_mime_type` + `response_schema` | Tool-forcing or inline prompt schema |
| `thinking_config=ThinkingConfig(thinking_budget=N)` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "..."}}` |
| `client.models.generate_content_stream()` | `client.converse_stream()` |
| XML tags in prompt | `##Section Name##` delimiters |

## Common Mistakes

### Forgetting the multimodal system prompt restriction
**Problem:** Copying full Gemini system instructions into Nova multimodal calls — task adherence degrades silently.
**Fix:** Move everything except persona to the user prompt.

### Passing `additionalModelRequestFields` when reasoning is disabled
**Problem:** Including `additionalModelRequestFields={"thinking": ...}` or any reasoning config when reasoning is not needed — Nova rejects unknown keys.
**Fix:** Omit `additionalModelRequestFields` entirely when reasoning is disabled. Only include it with `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "..."}}` when reasoning is needed.

### Using XML tags in Nova prompts
**Problem:** Keeping `<context>`, `<task>` etc. from the Gemini prompt — Nova ignores these as structural markers.
**Fix:** Replace with `##Section Name##` delimiters.

### Wrong media ordering
**Problem:** Putting text before images/video in the content array.
**Fix:** Media content blocks MUST come before the text block.

### Using OpenAPI schema format for tools
**Problem:** Copying Gemini's OpenAPI-style parameter schemas directly.
**Fix:** Convert to JSON Schema format in `inputSchema.json`.
