# Benchmark Onboarding Prompt Template

Port an existing benchmark into InspectAI format. The benchmark already exists (e.g., in OneClickEval YAML configs, AGI Model Lens Python, HuggingFace eval harnesses, or custom scripts) — this template guides conversion to the InspectAI framework.

Fill in the **USER INPUT** section below, then give the entire document to an AI assistant with this prompt:

```
I want to create an inspect AI benchmark.
I have provided all instructions for this in this document.
Follow the instructions closely and create this benchmark for me.
Do not look at any other files or folders and base your creation solely on this document.
If there are links you need to first read all the links before creating anything.

IMPORTANT: You MUST follow the workflow in exact order:
1. Read all source links first
2. Apply all mandatory adaptations (especially cross-backend token compatibility rules) BEFORE writing code
3. Create the files
4. Reflect: re-read your generated code and compare it against the source — verify field mappings, prompt format, scorer logic, and GenerateConfig all match. Fix any discrepancies before testing.
5. Run ALL THREE validation steps (smoke test, sanity check, log inspection) and fix any issues
6. Only report completion after tests pass — include test output as evidence

Do NOT skip the validation steps. The task is incomplete until tests pass.

Instructions document: /path-to/this-file.md
```

---

## USER INPUT (Edit this section)

### Benchmark Name
<!-- kebab-case, e.g., "medmcqa" -->

### Source
<!-- Where the existing benchmark lives. The AI will read this to infer prompt, scoring, etc. -->
<!-- Examples: -->
<!--   OneClickEval/oneclick/evals/k_shot/tasks/medmcqa/zs/olympus.yaml -->
<!--   https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/mmlu/mmlu.py -->
<!--   /path/to/existing/eval_script.py -->

### Dataset Path
<!-- Where the dataset lives. Either an S3 path to JSONL or a HuggingFace dataset identifier: -->
<!-- S3: s3://agi-model-lens-benchmarks-prod-us-east-1/agi-model-lens/data/medmcqa/medmcqa.jsonl -->
<!-- HuggingFace: cais/mmlu (split: test) -->

### Generation Parameters
<!-- Copy from source config decoding_params. This directly affects scoring strategy. -->
<!-- e.g., max_new_tokens: 1, temperature: 0, top_p: 1 -->
<!-- If unknown, leave blank — the AI must then use regex-based extraction in the scorer. -->

### Sample Record
<!-- ONE JSON record from the dataset. Needed so the AI can verify field mapping without S3 access. -->
```json
{
}
```

---

## INSTRUCTIONS FOR AI ASSISTANT

You are porting an existing benchmark to InspectAI. The evaluation logic already exists — your job is to translate it faithfully, not redesign it.

### Runtime Context

These benchmarks run against **vLLM endpoints in production** and are **validated against Bedrock during development**. The generated code must produce correct scores on both backends. When adapting generation parameters, choose the robust approach that works across backends — not a backend-specific hack.

### Workflow (follow in order — do NOT skip steps or report completion early)

1. **Read** all source links and understand the prompt template, scoring logic, and generation params
2. **Apply adaptations** (especially the mandatory cross-backend token compatibility rules for MCQ benchmarks) BEFORE writing code
3. **Create files** in `benchmarks/general/{benchmark_name}/`
4. **Reflect** — re-read your generated code and compare it line-by-line against the source:
   - Does `record_to_sample` map every field the solver and scorer need?
   - Does the prompt reproduce the source template character-for-character (plus any mandatory cross-backend adaptations)?
   - Does the scorer use the correct extraction pattern for the expected output format?
   - Does `GenerateConfig` match the adapted params (not the raw source values)?
   - Fix any discrepancies NOW, before running tests.
5. **Run all three validation steps** (smoke test, sanity check scores, inspect logs) — fix any issues found
6. **Only then** report completion to the user with test results as evidence

### CRITICAL CONSTRAINTS

- **DO NOT run `pip install`, `hatch install`, or any package installation commands.** This repository is managed by an external build system. You only create files — never install dependencies.
- **DO NOT create virtual environments or modify any environment.**
- **Only create files** in `benchmarks/general/{benchmark_name}/`. Do not modify files outside that directory.

### Source-Specific Mapping

Depending on the source format, find the key information in different places:

| If source is... | Find prompt in... | Find scoring in... | Find gen params in... |
|---|---|---|---|
| OneClickEval YAML | `turn_templates.prompt_template` (Jinja2) | `evaluation_metrics.*.post_processors` | `inf_args.decoding_params` |
| AGI Model Lens Python | The solver/prompt function | The scorer function | `generate_config` dict |
| HuggingFace / inspect_evals | The solver chain | The scorer (often built-in like `choice()`) | `GenerateConfig` in Task |
| Custom script | The inference loop | The evaluation function | The inference call args |

### Conversion Principles

1. **Score parity is the only goal.** The ported benchmark must produce the same scores as the original on the same data. Don't "improve" the scorer, prompt, or evaluation logic.
2. **Map concepts directly:**
   - Source pre-processing → `record_to_sample()` logic
   - Source prompt template → solver prompt formatting (see Solver Selection below)
   - Source post-processing / extraction → scorer answer extraction (see Scorer Selection below)
   - Source aggregation → InspectAI `metrics` list
   - Source decoding params → `GenerateConfig()` on `Task`
3. **Generation config drives scorer design:**
   - If source allows free-form output → scorer MUST implement robust extraction (regex with fallback)
   - Always strip special tokens (`<|begin_of_solution|>`, `<|end_of_solution|>`, etc.) before extraction

   - **MANDATORY — Cross-Backend Token Compatibility (MCQ only):** Source configs using `max_new_tokens: 1` (OneClickEval/vLLM) rely on vLLM's character-level tokenization where 1 token = 1 character for single-letter MCQ answers. This does NOT work on Bedrock Converse API, where 1 token = a full subword/word (e.g., "Looking", "The", "To"). The robust approach below works correctly on **both** backends (vLLM outputs "A" → extracted; Bedrock outputs "The answer is A" → extracted). **You MUST apply all three of the following adaptations when `max_new_tokens: 1` is used for MCQ:**
     1. Set `max_tokens=512` (not 1)
     2. Add an explicit prompt instruction: "Please respond with only the letter (A, B, C, or D) of the correct answer."
     3. Use a scorer that checks the first character of the completion for `[ABCD]`, falling back to the last `\b([ABCD])\b` match if the model is verbose
   - **This rule ONLY applies to MCQ benchmarks with `max_new_tokens: 1`.** Do NOT apply it to CoT, code generation, free-form, or any benchmark where `max_new_tokens` > 1.
4. **Keep it minimal.** No docstrings. No comments explaining what the source does. No `Args:`/`Returns:` blocks. The code should be short, direct, and correct — not a documentation artifact.
5. **Solver selection (in order of preference):**
   1. `generate()` directly — when `record_to_sample` already builds the full prompt as `Sample.input`
   2. `[prompt_template(TEMPLATE), generate()]` — when the solver just wraps input in a static template (use `{prompt}` placeholder for `state.input_text`)
   3. Custom `@solver` — ONLY when you need to access metadata, choices, multi-turn logic, or conditional formatting that can't be done in `record_to_sample`

   Prefer building the full prompt in `record_to_sample` over a custom `@solver`. A custom `@solver` that just concatenates fields and calls generate is unnecessary complexity.
6. **Scorer selection for MCQ:**
   1. PREFERRED: Use built-in `choice()` scorer with `multiple_choice()` solver — works across all backends without max_tokens adaptation. Set `choices` on `Sample` in `record_to_sample`.
   2. FALLBACK: Custom regex scorer with `max_tokens=512` — only when the source prompt format is incompatible with `multiple_choice()` (e.g., the source uses a non-standard option format or instructions that must be preserved character-for-character).

### Scoring Strategy Decision Tree

Based on the source config, choose the appropriate scorer pattern:

| Source Pattern | InspectAI Scorer |
|---|---|
| Standard MCQ (choices field available) | **PREFERRED:** Use `multiple_choice()` solver + `choice()` scorer. Set `choices` on Sample. Works on all backends without max_tokens adaptation. |
| `max_new_tokens: 1` + `ExactMatch` (MCQ with custom prompt) | **FALLBACK when `multiple_choice()` is incompatible:** Use `max_tokens=512`, add prompt instruction to respond with only the answer letter. Scorer: check `completion[0].upper()` for `[ABCD]` first; fall back to last `re.findall(r"\b([ABCD])\b", completion.upper())[-1]`. See cross-backend token compatibility above. |
| `RegexExtract` + `ExactMatch` | Apply same regex, compare extracted value |
| `"The correct answer is (X)"` format | Regex with main + fallback pattern |
| `\boxed{}` math answers | Use `GetLastBoxed` + `MathEqual` utilities |
| Numeric answers with tolerance | Parse numbers, compare with `abs(pred - target) <= threshold` |
| Code execution | Use `sandbox().exec()` with test cases. Task **MUST** set `sandbox='docker'` to enable sandbox access. |
| ROUGE / text generation | Use `rouge_score` library with custom `@metric` functions, report F1 |
| JSON extraction | Parse JSON, compute key/value overlap metrics |

Never invent a scoring strategy. Use exactly what the source uses.

**Custom metrics:** For benchmarks that report metrics other than accuracy (ROUGE, F1, ANLS, etc.), define custom `@metric` functions:
```python
from inspect_ai.scorer import metric, Metric, SampleScore
import numpy as np

@metric
def rouge1_score() -> Metric:
    def metric_fn(scores: list[SampleScore]) -> float:
        return float(np.mean([s.score.metadata["rouge1"] for s in scores]))
    return metric_fn

@scorer(metrics=[rouge1_score()])
def my_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        ...
        return Score(value=score_value, metadata={"rouge1": rouge1_f1})
    return score
```
The scorer stores per-metric values in `Score.metadata`, and each `@metric` aggregates them.

### Output Files

Create in `benchmarks/general/{benchmark_name}/`:

#### 1. `pyproject.toml`

```toml
[project]
name = "{benchmark_name}"
version = "1.0.0"
requires-python = "==3.12.*"
dependencies = [
    "amzn-agi-inspect==1.0.7",
    "numpy==2.2.6",
    "openai==2.6.0",
]

[tool.benchmark]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

Pin any additional dependencies with `==`.

#### 2. `{benchmark_name}.py`

```python
from __future__ import annotations
import re
from typing import Any
from inspect_ai import Task, task
from inspect_ai.dataset import json_dataset, hf_dataset, Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.solver import generate, prompt_template, solver, TaskState, Solver, Generate
from inspect_ai.scorer import scorer, Score, Scorer, Target, accuracy, stderr, CORRECT, INCORRECT

DATA_PATH = "<s3_path_or_hf_dataset_id>"

PROMPT_TEMPLATE = "<template with {prompt} placeholder, if applicable>"


def record_to_sample(record: dict[str, Any]) -> Sample:
    # Translate pre_processors logic here.
    # PREFERRED: build the full prompt here and set as input — then use generate() directly.
    ...


@task
def {benchmark_name}(dataset_path: str = DATA_PATH) -> Task:
    return Task(
        # For S3/JSONL:
        dataset=json_dataset(json_file=dataset_path, sample_fields=record_to_sample),
        # For HuggingFace:
        # dataset=hf_dataset(path=dataset_path, split="test", sample_fields=record_to_sample, trust=True),
        solver=[prompt_template(PROMPT_TEMPLATE), generate()],  # or just generate() if prompt is in record_to_sample
        scorer={name}_scorer(),
        config=GenerateConfig(
            max_tokens=<from source>,
            # temperature=<if specified>,
            # top_p=<if specified>,
        ),
        # sandbox='docker',  # Required for code execution scoring
        # epochs=1,  # Set explicitly if dataset has N-copies built-in (e.g., 32x)
    )
```

**When a custom solver IS needed** (multi-turn, conditional logic, metadata access):
```python
@solver
def {name}_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.user_prompt.text = <formatted prompt>
        return await generate(state)
    return solve
```

**When a custom scorer IS needed** (not using built-in `choice()`):
```python
@scorer(metrics=[accuracy(), stderr()])
def {name}_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        completion = state.output.completion.strip()
        completion = re.sub(r'<\|[^|]*\|>', '', completion).strip()
        # Extract answer using source post_processor logic
        ...
    return score
```

**For ChatML/pre-formatted message datasets:**
```python
from inspect_ai.model import ChatMessageUser, ChatMessageSystem

def record_to_sample(record: dict[str, Any]) -> Sample:
    messages = []
    for m in record["messages"]:
        if m["role"] == "system":
            messages.append(ChatMessageSystem(content=m["content"]))
        elif m["role"] == "user":
            messages.append(ChatMessageUser(content=m["content"]))
    return Sample(input=messages, target=...)
```
In this case, use `generate()` directly — no custom solver needed.

Requirements:
- ONE `@task` function with configurable `dataset_path` parameter
- Absolute imports only (no relative imports)
- `GenerateConfig` MUST be set with values from source `decoding_params` / `inf_args`
- Scorer must match original extraction logic exactly (regex patterns, normalization)
- Strip special tokens (`<|begin_of_solution|>`, etc.) before extraction
- No docstrings, no multi-line comments, no `Args:`/`Returns:` blocks
- Prefer `prompt_template()` + `generate()` over custom `@solver` when the solver just wraps input in a template
- Prefer building the full prompt in `record_to_sample` + bare `generate()` over a custom `@solver` that just concatenates fields
- If the dataset has N-copies built-in (e.g., `32x` in filename), set `epochs=1` explicitly
- Keep total file under 150 lines for simple benchmarks (MCQ, exact match)

#### 3. `README.md` (optional)

Only create if the benchmark has non-obvious setup requirements (e.g., Docker sandbox, external dependencies, dataset preprocessing). One paragraph max.

### Pre-Test Checklist (verify before running tests)

- [ ] Python file parses without syntax errors (`python3 -c "import ast; ast.parse(open('{benchmark_name}.py').read())"`)
- [ ] `pyproject.toml` has pinned deps
- [ ] `GenerateConfig` is cross-backend compatible (source `max_new_tokens: 1` for MCQ requires adaptation — see cross-backend token compatibility above)
- [ ] Scorer extraction logic matches source post_processors (test mentally with edge cases: empty output, reasoning before answer, boxed notation)
- [ ] `record_to_sample` maps all fields needed by solver and scorer
- [ ] Prompt output matches source template character-for-character
- [ ] File is under 150 lines for simple evals, under 300 for complex ones
- [ ] No unnecessary docstrings, no wrapper functions that add nothing
- [ ] No `__pycache__` or temp files

---

### REQUIRED: Reflect Before Testing

Before running any tests, re-read the generated `.py` file and compare it against the source config and prompt template. Specifically verify:

1. **Field mapping**: Every field accessed in the solver (`state.metadata["X"]`) and scorer (`target.text`) is set in `record_to_sample`. Mentally trace a sample record through the entire pipeline.
2. **Prompt fidelity**: Render the prompt mentally for the sample record in the USER INPUT section. Compare character-for-character against what the source template would produce (plus any mandatory adaptations like the MCQ instruction for cross-backend compatibility).
3. **Scorer extraction**: Given the prompt instruction you added, what will the model likely output? Will your extraction regex/logic correctly pull the answer from that output? Consider: (a) the model responds with just "B", (b) the model responds with "B. Some explanation", (c) the model ignores instructions and writes a paragraph.
4. **GenerateConfig**: Confirm you applied the adapted values (e.g., `max_tokens=512` for MCQ), NOT the raw source values (e.g., `max_new_tokens: 1`).

If you find any discrepancy, fix it before proceeding to tests.

---

### REQUIRED: Validate (Bedrock dev endpoint)

**⛔ STOP — The task is NOT complete until all three validation steps below pass. Do NOT report success to the user until you have run these tests and verified the results. Skipping these steps is a failure mode.**

**Why Bedrock for testing:** Production runs against vLLM, but Bedrock is used for dev validation because it requires no infrastructure setup. The code is written to work on both backends.

**Bedrock max_tokens cap:** Bedrock limits `max_tokens` to ~10,000 (model-dependent). If the source uses `max_new_tokens: 32768`, your code should set `max_tokens=32768` (matching production vLLM), but be aware that Bedrock will silently cap output during dev testing. This may cause lower scores on long-generation tasks (math CoT, code) during validation — that's expected and not a bug in your scorer.

**Region configuration:** Pass `-M region_name=us-east-1` to the `inspect eval` command. This passes the region directly to the boto client constructor and is the most reliable method. Alternatively, set `AWS_DEFAULT_REGION=us-east-1` as an environment variable.

**Model to use:** `bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0` (or another capable Bedrock model).

#### Step 1: Smoke test — must pass with zero errors

```bash
inspect eval {benchmark_name}.py --model bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0 -M region_name=us-east-1 --limit 5
```

If this fails, fix the error and re-run before proceeding. Common failures:
- `record_to_sample` field access errors (dataset schema mismatch)
- Missing imports or typos
- S3 dataset path inaccessible
- Scorer crashes on unexpected model output format
- Model outputs full words instead of expected single characters (scorer gets 0% accuracy) — means `max_tokens` is too low; increase it and add extraction logic (see cross-backend token compatibility)

#### Step 2: Sanity check scores — must be non-zero AND not 100%

```bash
inspect eval {benchmark_name}.py --model bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0 -M region_name=us-east-1 --limit 50
```

Verify:
- Scores are **non-zero** for a capable model (0% means the scorer is broken, not the model)
- Scores are **not 100%** unless the task is trivially easy — perfect scores on hard benchmarks usually mean the scorer is extracting the target from metadata rather than the model's output
- The extracted `answer` field in the log viewer shows plausible values (actual letters for MCQ, actual numbers for numeric tasks — not empty strings or garbage)

If scores are 0% or 100%, diagnose and fix before proceeding.

#### Step 3: Inspect the logs — must manually verify 3-5 samples

```bash
inspect log dump <log_file_path> | python3 -c "
import json, sys
data = json.load(sys.stdin)
samples = data.get('samples', [])
for i, s in enumerate(samples[:5]):
    print(f'--- Sample {i+1} ---')
    msgs = s.get('messages', [])
    for m in msgs:
        content = m['content']
        if isinstance(content, list):
            content = content[0].get('text', '')[:200]
        else:
            content = str(content)[:200]
        print(f'  [{m[\"role\"]}]: {content}')
    scores = s.get('scores', {})
    for name, sc in scores.items():
        print(f'  Score: {sc.get(\"value\")} | Answer: {sc.get(\"answer\")}')
    print(f'  Target: {s.get(\"target\")}')
    print()
"
```

For each sample verify:
- Does the prompt look correct? (Compare character-for-character with source template output)
- Does the model output look reasonable for the prompt?
- Does the scorer extract the right value from the model output?
- For wrong answers: is the model actually wrong, or is extraction failing?

If extraction is failing on >50% of samples, the scorer pattern doesn't match the model's output format. Revisit the scoring strategy decision tree.

**Only after all three steps pass with acceptable results may you report the task as complete.**
