# Harborline AI Engineering Project

Fictional Harborline Technologies policies plus HarborHub-style employee records, with a **seeded retrieval app** for employee questions about PTO, holidays, remote work, expenses, security, benefits, onboarding, equipment, leave, and conduct.

- Policies: [`corpus/README.md`](corpus/README.md)
- Structured records: [`data/README.md`](data/README.md)
- Gold questions: [`eval/gold_questions.json`](eval/gold_questions.json)

Default answer mode is **retrieve-only**. It does not need an API key. Set `HARBORLINE_ANSWER_MODE=llm` and `OPENAI_API_KEY` only if you want a generated answer.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Optional: Conda, if you prefer `environment.yml`
- Optional: Docker, for the deployment path
- Optional: an OpenAI-compatible API key, read from the environment (never committed)

## Setup

### Virtual environment (venv)

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Dev extras (pytest):

```powershell
pip install -r requirements-dev.txt
```

### Conda

```powershell
conda env create -f environment.yml
conda activate harborline
pip install -e .
```

### Secrets

Copy the example file and edit the local copy. **Do not commit `.env`.**

```powershell
copy .env.example .env
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Only for `HARBORLINE_ANSWER_MODE=llm` | Model provider key |
| `OPENAI_MODEL` | No | Default `gpt-4o-mini` |
| `OPENAI_BASE_URL` | No | Compatible gateway |
| `HARBORLINE_SEED` | No | Default `42` for eval sampling and LLM seed |
| `HARBORLINE_CHUNK_SIZE` | No | Deterministic window, default `900` |
| `HARBORLINE_CHUNK_OVERLAP` | No | Deterministic overlap, default `120` |
| `HARBORLINE_TOP_K` | No | Default `5` |
| `HARBORLINE_ANSWER_MODE` | No | `retrieve` (default) or `llm` |

`.gitignore` excludes `.env`, `.venv/`, and `.cache/`.

## Local run

Ingest builds a deterministic chunk index (useful as a cache; ask/eval also load sources directly):

```powershell
python -m harborline.cli ingest
```

Ask a policy question:

```powershell
python -m harborline.cli ask "How many PTO days do I get after my second anniversary?"
```

Ask with an employee record in context:

```powershell
python -m harborline.cli ask "Can I use PTO tomorrow?" --employee-id EMP-1014
```

JSON output:

```powershell
python -m harborline.cli ask "What is the US hotel cap?" --json
```

HTTP (same retriever):

```powershell
uvicorn harborline.api:app --reload --port 8000
```

```powershell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"query\":\"When does the 401k match vest?\"}"
```

## Evaluation

Gold items live in `eval/gold_questions.json`. Retrieval is scored as **recall@k**: a question passes if an expected source (and employee id, when required) appears in the top-k hits.

```powershell
python -m harborline.cli eval
python -m harborline.cli eval --limit 8 --json
pytest
```

`--limit` samples with `HARBORLINE_SEED` (default 42), so two runs with the same seed and limit return the same subset.

Chunking is a fixed sliding window. It does not shuffle documents. `PYTHONHASHSEED` is set to the same seed when you call `Settings.apply_seeds()`.

## Deployment

The image serves FastAPI. Pass secrets at **runtime**; do not bake keys into the image.

```powershell
docker build -t harborline-qa .
docker run --rm -p 8000:8000 --env-file .env harborline-qa
```

Or inject a single key:

```powershell
docker run --rm -p 8000:8000 -e HARBORLINE_ANSWER_MODE=retrieve harborline-qa
```

Health check: `GET /health`.  
Ask: `POST /ask`.  
Eval: `GET /eval`.

For a hosted deploy (Cloud Run, App Service, Fly.io), set the same env vars in the service configuration, attach `corpus/`, `data/`, and `eval/`, and keep `HARBORLINE_SEED=42` if you want eval numbers that match local runs.

## Reproducibility

| Knob | Default | Effect |
| --- | --- | --- |
| `HARBORLINE_SEED` | 42 | `random`, NumPy, eval sampling, LLM `seed` |
| `HARBORLINE_CHUNK_SIZE` / `OVERLAP` | 900 / 120 | Same text always yields the same chunks |
| TF-IDF retrieve | — | Stable sort: score desc, `chunk_id` asc |

## Project layout

```
corpus/             Policy documents (md, html, txt, pdf)
data/               Mock employees, PTO, benefits, tickets
eval/               Gold questions
harborline/         Ingest, retrieve, ask, eval, API
scripts/            PDF builder for companion policy sheets
tests/              Determinism and eval smoke tests
requirements.txt    Pip pins
requirements-dev.txt
environment.yml     Conda env
pyproject.toml      Package metadata
.env.example        Secret names only
Dockerfile
```
