"""A generated dataset has to say what rendered it.

The v4 retrain could not be attributed to a cause partly because nothing on
disk tied a 5,000-sheet set to the templates that produced it: the link lived
in prose in docs/ocr-eval-results.md and in whoever remembered. A manifest
makes the question mechanical, which is the whole point -- every future retrain
is a comparison between two datasets, and a comparison needs both operands
identified.

Torch-free on purpose: these exercise the manifest, not the renderer, so they
must run in the light venv that generates datasets (see dataset.py's guarded
torch import).
"""
import json

from inform.training.dataset import (
    MANIFEST_GLOB,
    fingerprint_inputs,
    generator_fingerprint,
    manifest_name,
    write_manifest,
)


def test_the_fingerprint_covers_the_generator_and_every_device_template():
    # Sensitivity is the property that matters and the one a hash cannot
    # assert about itself, so pin the inputs instead. A third device template
    # added later is covered without editing this test; a template moved out
    # of the glob fails it.
    names = sorted(p.name for p in fingerprint_inputs())

    assert "__init__.py" in names
    assert "inbody_270.html" in names
    assert "inbody_570.html" in names


def test_the_fingerprint_is_stable_across_calls():
    # Same source, same fingerprint -- otherwise two shards of one run would
    # disagree about what rendered them.
    assert generator_fingerprint() == generator_fingerprint()
    assert len(generator_fingerprint()) == 64


def test_the_manifest_records_what_a_retrain_needs_to_attribute_a_result(tmp_path):
    manifest = write_manifest(tmp_path, devices=("inbody_270",), n_per_device=3, seed_start=10)

    written = json.loads((tmp_path / manifest_name(10, 12)).read_text(encoding="utf-8"))

    assert written == manifest
    assert written["devices"] == ["inbody_270"]
    assert written["n_per_device"] == 3
    assert written["sheets"] == 3
    # Inclusive, and stated rather than derived: a held-out set is defined by
    # having a disjoint seed range, so the range is the thing being checked.
    assert written["seed_start"] == 10
    assert written["seed_end"] == 12
    assert written["generator_fingerprint"] == generator_fingerprint()


def test_shards_into_one_directory_each_keep_their_own_manifest(tmp_path):
    # A 5,000-sheet run is sharded over disjoint seed ranges into one output
    # directory. One fixed filename would leave the last shard's manifest
    # describing the whole set, claiming a fraction of the sheets present.
    write_manifest(tmp_path, devices=("inbody_270",), n_per_device=2, seed_start=0)
    write_manifest(tmp_path, devices=("inbody_270",), n_per_device=2, seed_start=2)

    found = sorted(p.name for p in tmp_path.glob(MANIFEST_GLOB))

    assert found == ["dataset.000000-000001.json", "dataset.000002-000003.json"]


def test_the_manifest_counts_every_device(tmp_path):
    manifest = write_manifest(
        tmp_path, devices=("inbody_270", "inbody_570"), n_per_device=2500, seed_start=0
    )

    assert manifest["sheets"] == 5000
    assert manifest["seed_end"] == 4999
