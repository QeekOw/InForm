"""Deploy the InForm API and Donut engine with `modal deploy modal_deploy.py`."""

from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
CHECKPOINT = "QeeeeK/donut-inbody"
REVISION = "f370e3de0b7dd6197ffe2033cdb7b30ae2b64548"


def download_checkpoint():
    from huggingface_hub import snapshot_download

    snapshot_download(
        CHECKPOINT,
        revision=REVISION,
        local_dir="/models/donut",
        ignore_patterns=["training_args.bin", "trainer_state.json"],
    )


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "backend/requirements.txt"))
    .pip_install(
        "torch==2.8.0",
        "torchvision==0.23.0",
        "transformers==5.0.0",
        "accelerate>=1.1",
        "sentencepiece",
        "protobuf",
        "Pillow>=10",
        "numpy>=1.24",
        "openai>=1.40",
    )
    .env({
        "INFORM_DONUT_CKPT": "/models/donut",
        "PYTHONPATH": "/app:/app/src",
        "ALLOWED_ORIGINS": "https://try-inform.vercel.app,https://in-form-chi.vercel.app",
    })
    .run_function(download_checkpoint)
    .add_local_dir(ROOT / "src", "/app/src", ignore=["__pycache__", "*.pyc"])
    .add_local_dir(ROOT / "backend", "/app/backend", ignore=["__pycache__", "*.pyc", ".env*"])
    .add_local_dir(ROOT / "data/samples", "/app/data/samples")
)
app = modal.App("inform", image=image)


# ponytail: read jobs live in memory; use shared storage before scaling beyond one container.
@app.function(
    cpu=2,
    memory=8192,
    max_containers=1,
    scaledown_window=300,
    timeout=600,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def api():
    import threading

    import torch

    from backend.main import app as web_app, get_engine, get_live_read_available
    from inform.extract import default_engine

    torch.set_num_threads(2)
    engine = default_engine()
    lock = threading.Lock()

    def predict(image_path):
        # Serialize model reads while HTTP polling stays concurrent.
        with lock, torch.inference_mode():
            return engine(image_path)

    web_app.dependency_overrides[get_engine] = lambda: predict
    web_app.dependency_overrides[get_live_read_available] = lambda: True
    return web_app
