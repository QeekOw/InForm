# Real end-to-end smoke test of the training pipeline (dataset generation
# -> fine-tune -> saved checkpoint -> reload), scoped to a tiny sheet count
# and a tiny public test-fixture model so it runs on CPU in seconds instead
# of the real ~5,000-sheet / donut-base run (which needs GPU + ~an hour of
# rendering, documented in docs/training.md). Requires network access to
# download the tiny fixture model and the `training` extra
# (pip install -e ".[dev,training]").
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
if not hasattr(torch, "__version__"):
    pytest.skip("torch is not installed (namespace dummy)", allow_module_level=True)
transformers = pytest.importorskip("transformers")

from inform.engines.donut import TASK_TOKEN as _ENGINE_TASK_TOKEN  # noqa: E402
from inform.training.dataset import TASK_TOKEN, generate_dataset  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

from inform.training import train as train_module  # noqa: E402
from inform.training.train import load_checkpoint, train  # noqa: E402


def test_engine_task_token_matches_training_token():
    # donut.py duplicates the literal to stay torch-free; they must not drift.
    assert _ENGINE_TASK_TOKEN == TASK_TOKEN

_TINY_MODEL = "optimum-internal-testing/tiny-random-VisionEncoderDecoderModel-donut"


def test_train_produces_a_loadable_checkpoint(tmp_path):
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "checkpoint"
    generate_dataset(data_dir, n_per_device=1)

    train(
        data_dir=data_dir,
        output_dir=output_dir,
        model_name_or_path=_TINY_MODEL,
        num_train_epochs=1,
        per_device_train_batch_size=1,
        max_target_length=64,  # tiny fixture model's max_position_embeddings is 128
    )

    assert (output_dir / "config.json").exists()

    processor, model = load_checkpoint(output_dir)
    pixel_values = processor(Image.new("RGB", (32, 32)), return_tensors="pt").pixel_values
    generated = model.generate(pixel_values, max_new_tokens=5)
    assert generated.shape[0] == 1


def test_dataloader_workers_reach_the_trainer(monkeypatch):
    # Decoding a ~3000x4000 JPEG and resizing it onto Donut's 2560x1920 canvas
    # happens every step. At the default of 0 workers that is serial with the
    # GPU rather than overlapped, so the knob has to be reachable.
    captured = {}
    real_args = train_module.Seq2SeqTrainingArguments

    def spy(**kwargs):
        captured.update(kwargs)
        return real_args(**kwargs)

    monkeypatch.setattr(train_module, "Seq2SeqTrainingArguments", spy)
    monkeypatch.setattr(
        train_module.Seq2SeqTrainer, "train", lambda self, **kw: None
    )

    data_dir = Path(tempfile.mkdtemp()) / "data"
    generate_dataset(data_dir, n_per_device=1)
    train_module.train(
        data_dir=data_dir,
        output_dir=data_dir.parent / "out",
        model_name_or_path=_TINY_MODEL,
        num_train_epochs=1,
        max_target_length=64,
        dataloader_num_workers=6,
    )

    assert captured["dataloader_num_workers"] == 6
