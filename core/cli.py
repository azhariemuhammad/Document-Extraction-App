"""Run an extraction without the UI:  python -m core.cli samples/x.pdf --profile full_document"""
import argparse
import mimetypes
from pathlib import Path

from core.pipeline import run_pipeline, save_outputs
from core.profiles import load_profiles
from core.providers import get_provider

parser = argparse.ArgumentParser()
parser.add_argument("file")
parser.add_argument("--profile", default="full_document")
args = parser.parse_args()

path = Path(args.file)
profile = load_profiles()[args.profile]
out = run_pipeline(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "", profile.instruction, get_provider(),
                   on_progress=lambda done, total: print(f"page {done}/{total}", flush=True))
print(save_outputs(out, f"{path.stem}__{profile.id}"))
print(out.run_info)
