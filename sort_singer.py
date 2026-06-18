#!/usr/bin/env python3
import argparse
import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".ogg"}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)  # dataset_custom/audio
    parser.add_argument("--language", default="english")
    parser.add_argument("--sample-rate", type=int, default=24000)
    parser.add_argument("--copy-only", action="store_true")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def normalize_singer_name(name: str) -> str:

    name = name.strip()

    # remove spaces, tabs, hyphens, underscores inside singer name
    name = re.sub(r"[\s\-_]+", "", name)

    # keep letters and numbers only
    name = re.sub(r"[^A-Za-z0-9]", "", name)

    if not name:
        raise ValueError("Empty singer name after normalization")

    return name


def parse_filename(path: Path):
    stem = path.stem

    m = re.match(r"^(.+?)_(\d{8})$", stem)
    if not m:
        raise ValueError(
            f"Filename does not match '<Singer Name>_XXXXXXXX.wav': {path.name}"
        )

    singer_raw = m.group(1)
    utt_id = m.group(2)

    song_id = utt_id[:4]
    segment_id = utt_id[4:]

    singer = normalize_singer_name(singer_raw)

    return singer, utt_id, song_id, segment_id


def convert_audio(src: Path, dst: Path, sample_rate: int, copy_only: bool):
    dst.parent.mkdir(parents=True, exist_ok=True)

    if copy_only:
        shutil.copy2(src, dst)
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]

    subprocess.run(cmd, check=True)


def main():
    args = parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    lang_dir = output_dir / args.language

    if not input_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {input_dir}")

    audio_files = []
    for p in input_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            audio_files.append(p)

    audio_files = sorted(audio_files)

    if not audio_files:
        print(f"[WARN] No audio files found under: {input_dir}")
        return

    manifest_rows = []
    singer_counts = {}
    processed = 0
    skipped = 0
    failed = 0

    for src in audio_files:
        try:
            singer, utt_id, song_id, segment_id = parse_filename(src)

            out_name = f"{singer}_{utt_id}.wav"
            dst = lang_dir / singer / out_name

            if dst.exists() and not args.overwrite:
                skipped += 1
                continue

            convert_audio(
                src=src,
                dst=dst,
                sample_rate=args.sample_rate,
                copy_only=args.copy_only,
            )

            singer_counts[singer] = singer_counts.get(singer, 0) + 1
            processed += 1

            manifest_rows.append(
                [
                    str(src),
                    str(dst),
                    args.language,
                    singer,
                    song_id,
                    segment_id,
                    utt_id,
                ]
            )

        except Exception as e:
            failed += 1
            print(f"[FAIL] {src}: {e}")

    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        with manifest_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "source_path",
                    "output_path",
                    "language",
                    "singer",
                    "song_id",
                    "segment_id",
                    "utt_id",
                ]
            )
            writer.writerows(manifest_rows)

    print()
    print("[SORT SUMMARY]")
    print(f"  input dir : {input_dir}")
    print(f"  output dir: {lang_dir}")
    print(f"  sample rate: {args.sample_rate}")
    print(f"  processed : {processed}")
    print(f"  skipped   : {skipped}")
    print(f"  failed    : {failed}")
    print()
    print("[SINGER COUNTS]")

    for singer, count in sorted(singer_counts.items()):
        print(f"  {singer}: {count}")


if __name__ == "__main__":
    main()