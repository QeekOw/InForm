import argparse
from pathlib import Path

from transformers import DonutProcessor, Seq2SeqTrainer, Seq2SeqTrainingArguments, VisionEncoderDecoderModel

from inform.training.dataset import TASK_TOKEN, DonutInBodyDataset

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
    per_device_train_batch_size: int = 1,
    learning_rate: float = 3e-5,
    max_target_length: int = 512,
    resume: bool = False,
    gradient_accumulation_steps: int = 4,
) -> Path:
    """Fine-tune Donut with cross-entropy next-token loss on target JSON (ADR-0002).

    Uses transformers' Seq2SeqTrainer, whose default forward pass already
    computes token-level cross-entropy against `labels` — no custom loss.
    Checkpoints every epoch (not just at the end) so a run interrupted
    partway through — a killed process, a lost remote session — can resume
    with `resume=True` instead of restarting from scratch.

    fp16 + gradient checkpointing keep donut-base's large fixed-canvas
    activations inside 8GB VRAM; gradient accumulation keeps the effective
    batch size reasonable at per-device batch_size=1 (see project memory:
    step-0 OOM at batch_size=2, no mixed precision, no checkpointing).
    """
    processor, model = build_model_and_processor(model_name_or_path)
    model.gradient_checkpointing_enable()
    dataset = DonutInBodyDataset(data_dir, processor, max_target_length=max_target_length)

    args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_train_epochs,
        per_device_train_batch_size=per_device_train_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        fp16=True,
        save_strategy="epoch",
        save_total_limit=2,
        logging_steps=10,
        remove_unused_columns=False,
        report_to=[],
    )
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=dataset)
    trainer.train(resume_from_checkpoint=resume)

    trainer.save_model(str(output_dir))
    processor.save_pretrained(str(output_dir))
    return output_dir


def _main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Donut on synthetic InBody sheets.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--resume", action="store_true", help="Resume from the last checkpoint in --output-dir")
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        model_name_or_path=args.model_name_or_path,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        resume=args.resume,
    )


if __name__ == "__main__":
    _main()
