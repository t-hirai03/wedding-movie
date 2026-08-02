#!/usr/bin/env python3
"""写真フォルダから Final Cut Pro 用の FCPXML（スライドショー）を生成する。"""

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape, quoteattr

FCPXML_VERSION = "1.13"
TIMEBASE = 3000

SEQUENCE_FORMATS = {
    "1080p30": ("FFVideoFormat1080p30", 1920, 1080, 30),
    "1080p2997": ("FFVideoFormat1080p2997", 1920, 1080, 30),
    "1080p24": ("FFVideoFormat1080p24", 1920, 1080, 24),
    "4k30": ("FFVideoFormat3840x2160p30", 3840, 2160, 30),
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def file_url(path: Path) -> str:
    return "file://" + quote(str(path.resolve()))


class Timeline:
    """フレーム数を有理数時間表記に変換する。FCPは分母を timebase に固定した形を要求する。"""

    def __init__(self, fps: int):
        self.fps = fps
        if TIMEBASE % fps:
            raise ValueError(f"fps {fps} は timebase {TIMEBASE} を割り切れない")
        self.frame_ticks = TIMEBASE // fps

    def frames(self, seconds: float) -> int:
        return max(1, round(seconds * self.fps))

    def time(self, frames: int) -> str:
        return "0s" if frames == 0 else f"{frames * self.frame_ticks}/{TIMEBASE}s"

    @property
    def frame_duration(self) -> str:
        return f"{self.frame_ticks}/{TIMEBASE}s"


def ken_burns(tl: Timeline, dur_frames: int, index: int, amount: float) -> list[str]:
    start, end = (1.0, 1.0 + amount) if index % 2 == 0 else (1.0 + amount, 1.0)
    return [
        "          <adjust-transform>",
        '            <param name="scale">',
        "              <keyframeAnimation>",
        f'                <keyframe time="{tl.time(0)}" value="{start:.4f} {start:.4f}" interp="linear" curve="linear"/>',
        f'                <keyframe time="{tl.time(dur_frames)}" value="{end:.4f} {end:.4f}" interp="linear" curve="linear"/>',
        "              </keyframeAnimation>",
        "            </param>",
        "          </adjust-transform>",
    ]


def build(photos: list[Path], args) -> str:
    fmt_name, width, height, fps = SEQUENCE_FORMATS[args.format]
    tl = Timeline(fps)
    clip_frames = tl.frames(args.duration)
    trans_frames = tl.frames(args.transition) if args.transition > 0 else 0

    resources = [
        f'    <format id="r0" name="{fmt_name}" frameDuration="{tl.frame_duration}"'
        f' width="{width}" height="{height}" colorSpace="1-1-1 (Rec. 709)"/>'
    ]
    spine = []
    offset = 0

    for i, photo in enumerate(photos):
        pw, ph = probe_size(photo)
        fmt_id, asset_id = f"rf{i}", f"ra{i}"
        name = photo.stem

        resources.append(
            f'    <format id="{fmt_id}" name="FFVideoFormatRateUndefined"'
            f' width="{pw}" height="{ph}" colorSpace="1-1-1 (Rec. 709)"/>'
        )
        resources.append(
            f'    <asset id="{asset_id}" name={quoteattr(name)} start="0s" duration="0s"'
            f' hasVideo="1" format="{fmt_id}" videoSources="1">'
        )
        resources.append(
            f'      <media-rep kind="original-media" src={quoteattr(file_url(photo))}/>'
        )
        resources.append("    </asset>")

        # 前のクリップとの境目にトランジションを置く。FCPは前後クリップのハンドルを
        # 消費するため、後続クリップの offset はずらさない（尺は変わらない）。
        if trans_frames and i > 0:
            spine.append(
                f'        <transition offset="{tl.time(offset - trans_frames // 2)}"'
                f' duration="{tl.time(trans_frames)}"/>'
            )

        spine.append(
            f'        <video ref="{asset_id}" offset="{tl.time(offset)}" name={quoteattr(name)}'
            f' start="0s" duration="{tl.time(clip_frames)}">'
        )
        spine.append(f'          <adjust-conform type="{args.conform}"/>')
        if args.ken_burns > 0:
            spine.extend(ken_burns(tl, clip_frames, i, args.ken_burns))
        spine.append("        </video>")

        offset += clip_frames

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!DOCTYPE fcpxml>",
        f'<fcpxml version="{FCPXML_VERSION}">',
        "  <resources>",
        *resources,
        "  </resources>",
    ]
    if args.library:
        lines.append(f"  <library location={quoteattr(file_url(Path(args.library)) + '/')}>")
    lines += [
        f"    <event name={quoteattr(args.event)}>",
        f"      <project name={quoteattr(args.project)}>",
        f'        <sequence format="r0" duration="{tl.time(offset)}" tcStart="0s"'
        ' tcFormat="NDF" audioLayout="stereo" audioRate="48k">',
        "        <spine>",
        *spine,
        "        </spine>",
        "        </sequence>",
        "      </project>",
        "    </event>",
    ]
    if args.library:
        lines.append("  </library>")
    lines.append("</fcpxml>")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("photos_dir", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--project", default="Wedding Movie")
    p.add_argument("--event", default="Wedding")
    p.add_argument("--library", help="取り込み先 .fcpbundle のパス（省略時は開いているライブラリ）")
    p.add_argument("--format", choices=SEQUENCE_FORMATS, default="1080p30")
    p.add_argument("--duration", type=float, default=5.0, help="1枚あたりの表示秒数")
    p.add_argument("--transition", type=float, default=1.0, help="トランジション秒数（0で無効）")
    p.add_argument("--ken-burns", type=float, default=0.12, help="ズーム量（0で無効）")
    p.add_argument("--conform", choices=["fit", "fill", "none"], default="fill")
    args = p.parse_args()

    photos = sorted(f for f in args.photos_dir.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES)
    if not photos:
        print(f"画像が見つかりません: {args.photos_dir}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build(photos, args), encoding="utf-8")
    print(f"生成: {args.output}  （写真 {len(photos)} 枚 / 尺 {len(photos) * args.duration:.1f}秒）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
