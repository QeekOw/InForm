import argparse
from pathlib import Path

from transformers import DonutProcessor, Seq2SeqTrainer, Seq2SeqTrainingArguments, VisionEncoderDecoderModel

from cera.training.dataset import TASK_TOKEN, DonutInBodyDataset

# The paper's contribution (ADR-0002); self-hosted, no per-call cost (ADR-0005).
DEFAULT_MODEL = "naver-clova-ix/donut-base"


def build_model_and_processor(model_name_or_path: str = DEFAULT_MODEL):
    """Load a Donut checkpoint and add the InBody task-prompt token.

    `model_name_or_path` also accepts a local checkpoint dir (for resuming
    or for loading a fine-tuned model) or a tiny test fixture model id.
    """
    processor = DonutProcessor.from_pretrained(model_name_or_path)
    model = VisionEncoderDecoderModel.from_pretrained(model_name_or_path)

    processor.tokenizer.add_special_tokens({"additional_special_tokens": [TASK_TOKEN]})
    model.decoder.resize_token_embeddings(len(processor.tokenizer))

    model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids(TASK_TOKEN)
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.eos_token_id = processor.tokenizer.eos_token_id

    return processor, model


def load_checkpoint(checkpoint_dir: Path):
    """Load a saved fine-tune for inference — proves the checkpoint round-trips."""
    processor = DonutProcessor.from_pretrained(str(checkpoint_dir))
    model = VisionEncoderDecoderModel.from_pretrained(str(checkpoint_dir))
    return processor, model


def train(
    data_dir: Path,
    output_dir: Path,
    model_name_or_path: str = DEFAULT_MODEL,
    num_train_epochs: int = 3,
    per_device_train_batch_size: int = 2,
    learning_rate: float = 3e-5,
    max_target_length: int = 512,
) -> Path:
    """Fine-tune Donut with cross-entropy next-token loss on target JSON (ADR-0002).

    Uses transformers' Seq2SeqTrainer, whose default forward pass already
    computes token-level cross-entropy against `labels` — no custom loss.
    """
    processor, model = build_model_and_processor(model_name_or_path)
    dataset = DonutInBodyDataset(data_dir, processor, max_target_length=max_target_length)

    args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        learning_rate=learning_rate,
        save_strategy="no",
        logging_steps=10,
        remove_unused_columns=False,
        report_to=[],
    )
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=dataset)
    trainer.train()

    trainer.save_model(str(output_dir))
    processor.save_pretrained(str(output_dir))
    return output_dir


def _main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Donut on synthetic InBody sheets.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        model_name_or_path=args.model_name_or_path,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )


if __name__ == "__main__":
    _main()
