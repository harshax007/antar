FROM python:3.11-slim

WORKDIR /app

# HF_HOME must be identical at BUILD time (when the models are baked in below) and at
# RUN time (when main.py forces HF_HUB_OFFLINE=1 and loads them from the local cache).
# Point it inside the image so the weights ship with it.
# These are set HERE, not only in app-config.json, because this app is deployed to
# AppSail as a Custom Runtime pulled from Docker Hub — that path builds the image from
# this file and does not read app-config.json. Anything the container needs at runtime
# has to be baked in here or set in the Catalyst console's Configuration tab.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.hf \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    ANTAR_DB=main.db \
    BRAIN_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# ── 1. CPU-ONLY PyTorch, installed FIRST and pinned ───────────────────────────
# sentence-transformers depends on torch. Installing it from PyPI on Linux pulls the
# CUDA build, which drags in nvidia-cublas / nvidia-cudnn / etc. — roughly 2.5 GB of
# GPU libraries that can never be used on an AppSail container. Taking torch from the
# CPU index first (~190 MB) means the requirements.txt install below sees the
# dependency already satisfied and never reaches for the CUDA wheel.
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.5.1

# ── 2. Application dependencies ───────────────────────────────────────────────
# Copied on its own so a code change does not invalidate this layer and force a full
# reinstall of scikit-learn / pandas / scipy / transformers on every build.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# -- Not root ------------------------------------------------------------------
# The service needs no privilege: it listens on a high port and writes only to /tmp
# (the staged database) and its own folder. Created here, after the system-wide pip
# install and before the models are cached, so the cache is owned by the user that
# reads it and no later layer has to re-own 300 MB.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin antar \
    && chown antar:antar /app
USER antar

# ── 3. Bake the Second Brain models into the image ────────────────────────────
# main.py sets HF_HUB_OFFLINE=1 so the container never blocks startup on a network
# fetch. That means the weights have to already be present, otherwise load_embedder()
# fails and the Brain comes up DEGRADED — semantic search and MO similarity silently
# off, which is exactly what the currently-live deployment does (/api/health reports
# brain_rows: 0, embedder_loaded: false).
#   BAAI/bge-small-en-v1.5           ~130 MB  — the 384-dim retrieval embedder
#   cross-encoder/ms-marco-MiniLM-L-6-v2 ~90 MB — stage-2 rerank
# Both embedder candidates are cached on purpose. settings.py defaults to bge-small but
# .env / .env.example override BRAIN_EMBEDDING_MODEL to all-MiniLM-L6-v2, and the two
# disagreeing is a silent "Brain degraded" in production: the container would hold one
# model and be asked for the other, load_embedder() would fail under HF_HUB_OFFLINE, and
# semantic search would just quietly be off. app-config.json pins the runtime value to
# bge-small; caching MiniLM too (~90 MB) means a stale env var in the Catalyst console
# cannot resurrect that failure.
RUN python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); \
SentenceTransformer('all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512); \
print('second brain models cached')"

# Note: llama-cpp-python and the build-essential/cmake toolchain it needed are NOT
# installed. It loads models/phi2.ggml, which is not in the repo (models/ holds only a
# README), so it could never initialise; local_intent_classifier.py already falls back
# to the keyword classifier, which is what has been running in production all along.

# ── 4. Application code ───────────────────────────────────────────────────────
COPY --chown=antar:antar . /app

# Catalyst AppSail injects the port at runtime; run.py reads X_ZOHO_CATALYST_LISTEN_PORT.
EXPOSE 9000

CMD ["python3", "run.py"]
