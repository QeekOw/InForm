---
title: InForm Donut Engine
emoji: 🍩
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# InForm — Donut Engine (Module 1 OCR)

Self-hosted Document Understanding Transformer (Donut) fine-tuned on InBody 270 and 570 result sheets.

- Loads checkpoint directly from Hugging Face Hub (ADR-0010).
- Accepts an InBody result sheet image and outputs structured extraction with unread and flagged fields.
- Complies with ADR-0005: never falls back to cloud VLM.
