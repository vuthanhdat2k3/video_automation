# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# project-identity
- This is a 2D animation studio project, NOT specifically "chibi" — avoid using "chibi" in naming, labels, and descriptions. Confidence: 0.75

# workflow
- ComfyUI should be installed inside the pipeline project directory (`~/pipeline`), not in the home directory. Confidence: 0.70
- Use `uv` as the Python package manager for running commands and installing dependencies. Confidence: 0.65

# docker
- Avoid mapping PostgreSQL to port 5432 on Docker Desktop WSL2 — the Docker proxy interferes with auth. Map to an alternate port like 15432:5432 instead. Confidence: 0.85

