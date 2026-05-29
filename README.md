# Cert Lab

Herramienta propia para estudiar y demostrar fundamentos de **GitHub Foundations**,
**Microsoft AZ-900** y **PCEP** con FastAPI, SQLite, Docker y CI.

La interfaz y el contenido visible están en español. Las preguntas son originales:
este repositorio no contiene dumps, preguntas reales de examen ni copias largas de
material oficial. Solo enlaza objetivos públicos para orientar el estudio.

## Objetivos oficiales

- GitHub Foundations: <https://docs.github.com/en/get-started/showcase-your-expertise-with-github-certifications/about-github-certifications>
- Microsoft Azure Fundamentals AZ-900: <https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/>
- PCEP: <https://pythoninstitute.org/pcep>

## Technical Notes

Cert Lab is a small server-rendered FastAPI application. It loads versioned YAML
content from `content/es`, stores local progress in SQLite, and keeps the public
study surface safe for a portfolio repository.

### Run locally

```bash
uv sync --dev
uv run uvicorn cert_lab.app:app --reload
```

Open <http://127.0.0.1:8000>.

### Validate

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
docker build -t cert-lab .
```

### Data

By default the app writes progress to `data/cert_lab.sqlite3`. Override it with:

```bash
CERT_LAB_DATABASE_URL=sqlite:///./data/cert_lab.sqlite3
```

## License

MIT
