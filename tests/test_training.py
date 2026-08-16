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
transformers = pytest.importorskip("transformers")

from cera.training.dataset import generate_dataset  # noqa: E402
from cera.training.train import load_checkpoint, train  # noqa: E402

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
