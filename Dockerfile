FROM python:3.12-slim
RUN pip install --no-cache-dir --upgrade pip

# Fully-pinned + hashed deps (generated from requirements.in via `uv pip compile
# --universal --generate-hashes`); --require-hashes makes the build fail on any
# drift or tampering.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
