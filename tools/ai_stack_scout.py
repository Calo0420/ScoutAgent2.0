"""
AI Stack Scout Tools — covers A7 (AI Stack Assessment)
Scans for AI/ML infrastructure: GPU drivers, CUDA, container runtimes,
model serving frameworks, vector databases, data pipelines.
Read-only SSH. Zero writes to client environment.
"""
import paramiko
import shlex
from datetime import datetime


def _ssh_run(client, cmd):
    _, stdout, _ = client.exec_command(cmd, timeout=15)
    return stdout.read().decode().strip()


def assess_ai_stack(host: str, username: str, key_path: str = None, password: str = None, port: int = 22) -> dict:
    """
    A7 — AI Stack Assessment: end-to-end review of AI/ML readiness.
    Checks GPU, CUDA, container runtime, model serving, vector DBs,
    data pipelines, security posture, and governance gaps.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {"hostname": host, "username": username, "port": port, "timeout": 10}
    if key_path:
        connect_kwargs["key_filename"] = key_path
    else:
        connect_kwargs["password"] = password

    try:
        client.connect(**connect_kwargs)
    except Exception as e:
        return {"error": str(e), "host": host, "scanned_at": datetime.utcnow().isoformat()}

    try:
        # ── GPU & CUDA ─────────────────────────────────────────────────────────
        gpu = {
            "nvidia_smi":      _ssh_run(client, "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null"),
            "cuda_version":    _ssh_run(client, "nvcc --version 2>/dev/null | grep release | awk '{print $6}' | cut -c2-"),
            "cuda_devices":    _ssh_run(client, "nvidia-smi --list-gpus 2>/dev/null | wc -l"),
            "gpu_memory_free": _ssh_run(client, "nvidia-smi --query-gpu=memory.free --format=csv,noheader 2>/dev/null"),
            "rocm_version":    _ssh_run(client, "rocm-smi --version 2>/dev/null | head -1"),  # AMD GPU
        }

        # ── Container & Orchestration ──────────────────────────────────────────
        containers = {
            "docker":           _ssh_run(client, "docker --version 2>/dev/null"),
            "docker_nvidia":    _ssh_run(client, "docker info 2>/dev/null | grep -i nvidia"),
            "podman":           _ssh_run(client, "podman --version 2>/dev/null"),
            "kubernetes":       _ssh_run(client, "kubectl version --client 2>/dev/null | head -1"),
            "helm":             _ssh_run(client, "helm version 2>/dev/null | head -1"),
            "nvidia_container": _ssh_run(client, "nvidia-container-toolkit --version 2>/dev/null"),
        }

        # ── Model Serving Frameworks ───────────────────────────────────────────
        serving = {
            "triton":     _ssh_run(client, "which tritonserver 2>/dev/null || systemctl is-active triton 2>/dev/null"),
            "torchserve": _ssh_run(client, "torchserve --version 2>/dev/null"),
            "ollama":     _ssh_run(client, "ollama --version 2>/dev/null"),
            "vllm":       _ssh_run(client, "python3 -c 'import vllm; print(vllm.__version__)' 2>/dev/null"),
            "ray":        _ssh_run(client, "python3 -c 'import ray; print(ray.__version__)' 2>/dev/null"),
            "mlflow":     _ssh_run(client, "mlflow --version 2>/dev/null"),
            "bentoml":    _ssh_run(client, "bentoml --version 2>/dev/null"),
            "fastapi":    _ssh_run(client, "python3 -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null"),
        }

        # ── Vector Databases ───────────────────────────────────────────────────
        vector_dbs = {
            "chroma":       _ssh_run(client, "python3 -c 'import chromadb; print(chromadb.__version__)' 2>/dev/null"),
            "qdrant":       _ssh_run(client, "systemctl is-active qdrant 2>/dev/null || docker ps 2>/dev/null | grep qdrant"),
            "weaviate":     _ssh_run(client, "systemctl is-active weaviate 2>/dev/null || docker ps 2>/dev/null | grep weaviate"),
            "milvus":       _ssh_run(client, "systemctl is-active milvus 2>/dev/null || docker ps 2>/dev/null | grep milvus"),
            "pinecone_sdk": _ssh_run(client, "python3 -c 'import pinecone; print(pinecone.__version__)' 2>/dev/null"),
            "pgvector":     _ssh_run(client, "psql -U postgres -c 'SELECT extversion FROM pg_extension WHERE extname = \"vector\";' 2>/dev/null"),
        }

        # ── ML Frameworks ─────────────────────────────────────────────────────
        frameworks = {
            "pytorch":       _ssh_run(client, "python3 -c 'import torch; print(torch.__version__, \"CUDA:\", torch.cuda.is_available())' 2>/dev/null"),
            "tensorflow":    _ssh_run(client, "python3 -c 'import tensorflow as tf; print(tf.__version__)' 2>/dev/null"),
            "transformers":  _ssh_run(client, "python3 -c 'import transformers; print(transformers.__version__)' 2>/dev/null"),
            "langchain":     _ssh_run(client, "python3 -c 'import langchain; print(langchain.__version__)' 2>/dev/null"),
            "scikit_learn":  _ssh_run(client, "python3 -c 'import sklearn; print(sklearn.__version__)' 2>/dev/null"),
            "anthropic_sdk": _ssh_run(client, "python3 -c 'import anthropic; print(anthropic.__version__)' 2>/dev/null"),
            "openai_sdk":    _ssh_run(client, "python3 -c 'import openai; print(openai.__version__)' 2>/dev/null"),
        }

        # ── Data Pipeline ─────────────────────────────────────────────────────
        pipelines = {
            "airflow": _ssh_run(client, "airflow version 2>/dev/null"),
            "spark":   _ssh_run(client, "spark-submit --version 2>/dev/null | head -1"),
            "kafka":   _ssh_run(client, "systemctl is-active kafka 2>/dev/null || docker ps 2>/dev/null | grep kafka"),
            "dbt":     _ssh_run(client, "dbt --version 2>/dev/null | head -1"),
            "prefect": _ssh_run(client, "prefect version 2>/dev/null"),
        }

        # ── Security & Governance Gaps ────────────────────────────────────────
        security_gaps = []

        model_dirs = _ssh_run(client, "find /opt /home /var -name '*.bin' -o -name '*.gguf' -o -name '*.pt' 2>/dev/null | head -5")
        if model_dirs:
            # SECURITY: model_dirs comes from a remote find result on the scanned
            # target. Never interpolate untrusted remote output directly into a
            # shell command — shlex.quote() neutralizes shell metacharacters
            # (;, |, `, $(), etc) a maliciously named file could use for
            # command injection against the target.
            first_path = shlex.quote(model_dirs.splitlines()[0])
            perms = _ssh_run(client, f"ls -la {first_path} 2>/dev/null")
            if "rw-rw-rw" in perms or "rwxrwxrwx" in perms:
                security_gaps.append("Model files found with world-writable permissions")

        api_ports = _ssh_run(client, "ss -tlnp | grep -E ':8000|:8080|:8888|:11434|:7860' | awk '{print $4}'")
        if api_ports:
            security_gaps.append(f"Potential AI API endpoints exposed without confirmed auth: {api_ports}")

        # Detect credential files by EXISTENCE only (no content read) — permitted
        # under the data classification policy. We deliberately do NOT grep their
        # contents; reading a credential file is gated by Gatekeeper below.
        cred_hits = _ssh_run(client, "find /opt /home /root /etc -maxdepth 6 -type f \\( -name '*.env' -o -name '*.pem' -o -name '*.key' -o -name 'id_rsa' -o -name 'credentials' \\) 2>/dev/null | head -10")
        cred_files = [f.strip() for f in cred_hits.splitlines() if f.strip()]
        if cred_files:
            # Per data classification policy (CIS Control 3 / NIST 800-53 AC-3),
            # reading a credential file's CONTENTS is gated by Gatekeeper.
            # Detection is allowed; the read is requested and expected to be blocked.
            try:
                from gatekeeper_client import request_access
                blocked = [cf for cf in cred_files if not request_access(cf, action="read")]
            except Exception:
                blocked = []
            if blocked:
                security_gaps.append(
                    f"Credential files DETECTED ({len(cred_files)}) and flagged as risk: "
                    f"{', '.join(cred_files)}. Content read BLOCKED by Gatekeeper per data "
                    f"classification policy (CIS Control 3 / NIST 800-53 AC-3) — existence "
                    f"reported, contents NOT accessed."
                )
            else:
                security_gaps.append(
                    f"Credential files detected ({len(cred_files)}): {', '.join(cred_files)} "
                    f"— flagged as risk (contents not read)."
                )

    finally:
        client.close()

    # ── Readiness Rating ───────────────────────────────────────────────────────
    has_gpu        = bool(gpu["nvidia_smi"] or gpu["rocm_version"])
    has_serving    = any(v for v in serving.values() if v)
    has_vector_db  = any(v for v in vector_dbs.values() if v)
    has_frameworks = sum(1 for v in frameworks.values() if v)

    if has_gpu and has_serving and has_vector_db and has_frameworks >= 3:
        readiness = "PRODUCTION_READY"
    elif has_gpu and has_frameworks >= 2:
        readiness = "DEVELOPMENT_READY"
    elif has_frameworks >= 1:
        readiness = "EARLY_STAGE"
    else:
        readiness = "NOT_STARTED"

    return {
        "host":             host,
        "gpu":              {k: v for k, v in gpu.items() if v},
        "containers":       {k: v for k, v in containers.items() if v},
        "model_serving":    {k: v for k, v in serving.items() if v},
        "vector_databases": {k: v for k, v in vector_dbs.items() if v},
        "ml_frameworks":    {k: v for k, v in frameworks.items() if v},
        "data_pipelines":   {k: v for k, v in pipelines.items() if v},
        "security_gaps":    security_gaps,
        "ai_readiness":     readiness,
        "summary": (
            f"GPU: {'YES' if has_gpu else 'NO'} | "
            f"Model Serving: {'YES' if has_serving else 'NO'} | "
            f"Vector DB: {'YES' if has_vector_db else 'NO'} | "
            f"ML Frameworks: {has_frameworks} detected | "
            f"Readiness: {readiness}"
        ),
    }
