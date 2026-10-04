#!/usr/bin/env python3
"""Build deterministic paper tables and vector figures from registered Run 010 outputs."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

from shockbridge_state_risk.data.download import sha256_file

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "reports/methodology/state_vintage_robustness_run010_v1.audit.json"
EPISODE_PATH = ROOT / "data/processed/state_vintage_episodes_run010_v1.csv"
INPUT_HASHES = {
    AUDIT_PATH: "6631f7ad8fd2bffc2d1d606e39a187029ea96d5adac61269af4c25f3d6584b81",
    EPISODE_PATH: "67dec146bae186bc9e5680be36ec6caf80443bbc3449af99601c4a8c53e5001b",
}
WINDOWS = (96, 120, 144)
VINTAGES = ("point_in_time", "latest_vintage")
COLORS = {"point_in_time": "#1F77B4", "latest_vintage": "#D95F02"}


class PaperArtifactError(ValueError):
    """Raised when a paper artifact cannot be traced to the frozen Run 010 bundle."""


def _canonical(value: float) -> float:
    return float(f"{float(value):.12g}")


def _verify_inputs() -> None:
    for path, expected in INPUT_HASHES.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise PaperArtifactError(f"Registered Run 010 input is missing or changed: {path}")


def _write_staged_text(path: Path, content: str) -> None:
    if path.exists():
        raise PaperArtifactError(f"Staged paper artifact already exists: {path}")
    path.write_text(content, encoding="utf-8")


def _csv_text(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _svg_text(
    x: float,
    y: float,
    value: str,
    *,
    size: int = 14,
    anchor: str = "middle",
    weight: str = "normal",
    fill: str = "#202124",
    rotate: Optional[int] = None,
) -> str:
    transform = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{fill}"{transform}>{html.escape(value)}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, **attributes: Any) -> str:
    rendered = " ".join(f'{key.replace("_", "-")}="{value}"' for key, value in attributes.items())
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {rendered}/>'


def _geometry_svg(audit: Mapping[str, Any]) -> str:
    width, height = 1240, 720
    top, bottom = 145.0, 600.0
    panel_width, gap = 330.0, 55.0
    lefts = (80.0, 80.0 + panel_width + gap, 80.0 + 2.0 * (panel_width + gap))
    panels = (
        ("Second principal cosine, p10", "second_principal_cosine_p10", 1.0, 0.90),
        ("Normalized projector distance, p90", "projector_distance_p90", 0.8, 0.35),
        ("Core-breach rate", "core_breach_rate", 0.6, None),
    )
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        "<title>Run 010 full-panel factor geometry by data vintage</title>",
        (
            "<desc>Three panels compare second principal cosine, normalized projector distance, "
            "and core-breach rate for 96, 120, and 144 month rolling histories.</desc>"
        ),
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        _svg_text(
            width / 2, 35, "Run 010: full-panel geometry by data vintage", size=22, weight="bold"
        ),
        _svg_text(
            width / 2,
            62,
            "Matched observations and missingness; lower cosine and higher distance indicate "
            "instability",
            size=13,
            fill="#4A4A4A",
        ),
    ]
    legend_y = 88.0
    for offset, vintage in ((-105.0, "point_in_time"), (80.0, "latest_vintage")):
        x = width / 2 + offset
        lines.append(f'<circle cx="{x:.2f}" cy="{legend_y:.2f}" r="5" fill="{COLORS[vintage]}"/>')
        lines.append(
            _svg_text(
                x + 10,
                legend_y + 5,
                "Point in time" if vintage == "point_in_time" else "Latest vintage",
                size=13,
                anchor="start",
            )
        )
    for panel_index, (title, metric, maximum, threshold) in enumerate(panels):
        left = lefts[panel_index]
        right = left + panel_width
        lines.append(_svg_text((left + right) / 2, top - 12, title, size=15, weight="bold"))
        lines.append(_line(left, top, left, bottom, stroke="#202124", stroke_width="1.2"))
        lines.append(_line(left, bottom, right, bottom, stroke="#202124", stroke_width="1.2"))
        ticks = 5 if maximum == 1.0 else (4 if maximum == 0.8 else 3)
        for tick in range(ticks + 1):
            value = maximum * tick / ticks
            y = bottom - (bottom - top) * value / maximum
            lines.append(_line(left - 5, y, right, y, stroke="#E0E0E0", stroke_width="1"))
            label = f"{value:.1f}" if metric != "core_breach_rate" else f"{value:.0%}"
            lines.append(_svg_text(left - 10, y + 5, label, size=12, anchor="end"))
        x_positions = [left + panel_width * (index + 1) / 4 for index in range(3)]
        for x, window in zip(x_positions, WINDOWS):
            lines.append(_svg_text(x, bottom + 25, str(window), size=13))
        lines.append(
            _svg_text((left + right) / 2, bottom + 51, "Rolling history (months)", size=13)
        )
        if threshold is not None:
            threshold_y = bottom - (bottom - top) * threshold / maximum
            lines.append(
                _line(
                    left,
                    threshold_y,
                    right,
                    threshold_y,
                    stroke="#666666",
                    stroke_width="1.5",
                    stroke_dasharray="6 5",
                )
            )
            lines.append(
                _svg_text(
                    right - 3,
                    threshold_y - 6,
                    f"failure reference {threshold:.2f}",
                    size=11,
                    anchor="end",
                    fill="#555555",
                )
            )
        for vintage in VINTAGES:
            points = []
            for x, window in zip(x_positions, WINDOWS):
                value = float(
                    audit["geometry_summary"][vintage]["full"]["windows"][str(window)][metric]
                )
                y = bottom - (bottom - top) * value / maximum
                points.append((x, y, value))
            lines.append(
                '<polyline points="{}" fill="none" stroke="{}" stroke-width="2.5"/>'.format(
                    " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points), COLORS[vintage]
                )
            )
            for x, y, value in points:
                lines.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{COLORS[vintage]}" '
                    'stroke="#FFFFFF" stroke-width="1.2"/>'
                )
                label = f"{value:.3f}" if metric != "core_breach_rate" else f"{value:.1%}"
                dy = -10 if vintage == "point_in_time" else 20
                lines.append(_svg_text(x, y + dy, label, size=10, fill=COLORS[vintage]))
        lines.append(_svg_text(left + 12, top + 20, chr(65 + panel_index), size=16, weight="bold"))
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _month_number(value: str) -> int:
    prefix, year, month = value.split("-")
    if prefix != "month":
        raise PaperArtifactError(f"Invalid episode month: {value}")
    return int(year) * 12 + int(month) - 1


def _episode_svg(episodes: Sequence[Mapping[str, str]]) -> str:
    width, height = 1240, 570
    left, right, top, bottom = 235.0, 1170.0, 90.0, 485.0
    start, end = _month_number("month-2014-02"), _month_number("month-2025-10")
    selected = [row for row in episodes if row["panel_variant"] == "full"]
    lookup = {(row["panel_vintage"], int(row["rolling_months"])): row for row in selected}
    lines = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        "<title>Run 010 persistent full-panel geometry-breach episodes</title>",
        (
            "<desc>Six timelines compare point-in-time and latest-vintage breach episodes for "
            "96, 120, and 144 month rolling histories.</desc>"
        ),
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        _svg_text(
            width / 2,
            35,
            "Run 010: persistent full-panel geometry-breach episodes",
            size=22,
            weight="bold",
        ),
        _svg_text(
            width / 2,
            62,
            "Primary 3-month onset / 3-month recovery; episodes are descriptive, not causal "
            "break dates",
            size=13,
            fill="#4A4A4A",
        ),
    ]
    row_order = [(window, vintage) for window in WINDOWS for vintage in VINTAGES]
    row_gap = (bottom - top) / len(row_order)
    for year in range(2015, 2026):
        month = year * 12
        x = left + (right - left) * (month - start) / (end - start)
        lines.append(_line(x, top, x, bottom, stroke="#E0E0E0", stroke_width="1"))
        lines.append(_svg_text(x, bottom + 28, str(year), size=11, rotate=-45, anchor="end"))
    for index, (window, vintage) in enumerate(row_order):
        y = top + row_gap * (index + 0.5)
        label = f"{window}m · {'point in time' if vintage == 'point_in_time' else 'latest vintage'}"
        lines.append(_svg_text(left - 15, y + 5, label, size=12, anchor="end"))
        lines.append(_line(left, y, right, y, stroke="#EEEEEE", stroke_width="1"))
        row = lookup.get((vintage, window))
        if row is None:
            raise PaperArtifactError(f"Missing full-panel episode: {window}, {vintage}")
        episode_start = _month_number(row["start_month"])
        episode_end = _month_number(row["end_month"])
        x1 = left + (right - left) * (episode_start - start) / (end - start)
        x2 = left + (right - left) * (episode_end - start) / (end - start)
        lines.append(
            _line(
                x1,
                y,
                x2,
                y,
                stroke=COLORS[vintage],
                stroke_width="12",
                stroke_linecap="round",
            )
        )
        lines.append(f'<circle cx="{x1:.2f}" cy="{y:.2f}" r="5" fill="{COLORS[vintage]}"/>')
        lines.append(f'<circle cx="{x2:.2f}" cy="{y:.2f}" r="5" fill="{COLORS[vintage]}"/>')
        lines.append(
            _svg_text(
                (x1 + x2) / 2,
                y - 12,
                f"{row['start_month'].removeprefix('month-')}-"
                f"{row['end_month'].removeprefix('month-')}",
                size=10,
                fill=COLORS[vintage],
            )
        )
    lines.extend(
        [
            _line(left, bottom, right, bottom, stroke="#202124", stroke_width="1.2"),
            _svg_text((left + right) / 2, height - 24, "Calendar month", size=13),
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def build(output_directory: Path) -> dict[str, Any]:
    _verify_inputs()
    staged_directory = output_directory.with_name(output_directory.name + ".part")
    if output_directory.exists() or staged_directory.exists():
        raise PaperArtifactError(
            f"Paper artifact bundle is immutable and already exists: {output_directory}"
        )
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    with EPISODE_PATH.open(newline="", encoding="utf-8") as stream:
        episodes = list(csv.DictReader(stream))
    if audit["primary_classification"] != "LATEST_VINTAGE_ROBUST_INSTABILITY":
        raise PaperArtifactError("Run 010 classification differs from the registered result.")

    geometry_rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        for vintage in VINTAGES:
            summary = audit["geometry_summary"][vintage]["full"]["windows"][str(window)]
            numeric_values = (
                summary["second_principal_cosine_p10"],
                summary["projector_distance_p90"],
                summary["core_breach_rate"],
                summary["weak_identification_coincidence_rate_among_breaches"],
                summary["mean_off_diagonal_gram_drift_share"],
            )
            if not all(math.isfinite(float(value)) for value in numeric_values):
                raise PaperArtifactError(f"Non-finite geometry summary: {window}, {vintage}")
            geometry_rows.append(
                {
                    "rolling_months": window,
                    "vintage": vintage,
                    "common_origins": summary["common_origins"],
                    "second_principal_cosine_p10": summary["second_principal_cosine_p10"],
                    "projector_distance_p90": summary["projector_distance_p90"],
                    "core_breach_rate": summary["core_breach_rate"],
                    "weak_identification_coincidence_rate": summary[
                        "weak_identification_coincidence_rate_among_breaches"
                    ],
                    "mean_off_diagonal_gram_drift_share": summary[
                        "mean_off_diagonal_gram_drift_share"
                    ],
                    "window_specific_geometry_failure": summary["window_specific_geometry_failure"],
                }
            )
    value_rows = [
        {"feature_id": feature, **values}
        for feature, values in audit["value_revision_summary"].items()
    ]
    bootstrap_rows: list[dict[str, Any]] = []
    for window in WINDOWS:
        point = audit["geometry_summary"]["point_in_time"]["full"]["windows"][str(window)]
        latest = audit["geometry_summary"]["latest_vintage"]["full"]["windows"][str(window)]
        intervals = audit["dependent_summary_uncertainty"][str(window)]["12"]
        for statistic, point_key in (
            ("second_principal_cosine_p10_difference", "second_principal_cosine_p10"),
            ("projector_distance_p90_difference", "projector_distance_p90"),
            ("core_breach_rate_difference", "core_breach_rate"),
        ):
            bootstrap_rows.append(
                {
                    "rolling_months": window,
                    "block_months": 12,
                    "statistic": statistic,
                    "latest_minus_point_estimate": _canonical(
                        float(latest[point_key]) - float(point[point_key])
                    ),
                    "lower_95": intervals[statistic]["lower_95"],
                    "upper_95": intervals[statistic]["upper_95"],
                    "full_factor_uncertainty_claimed": False,
                }
            )

    full_episodes = [row for row in episodes if row["panel_variant"] == "full"]
    full_episode_keys = {
        (row["panel_vintage"], int(row["rolling_months"])) for row in full_episodes
    }
    expected_episode_keys = {(vintage, window) for vintage in VINTAGES for window in WINDOWS}
    if (
        len(full_episodes) != len(expected_episode_keys)
        or full_episode_keys != expected_episode_keys
    ):
        raise PaperArtifactError("Full-panel episode coverage differs from the registered design.")

    paths = {
        "geometry_table": staged_directory / "run010_table_geometry_v1.csv",
        "value_table": staged_directory / "run010_table_value_differences_v1.csv",
        "bootstrap_table": staged_directory / "run010_table_bootstrap_primary_v1.csv",
        "geometry_figure": staged_directory / "run010_figure_geometry_v1.svg",
        "episode_figure": staged_directory / "run010_figure_episodes_v1.svg",
        "metadata": staged_directory / "run010_paper_artifacts_v1.json",
    }
    staged_directory.parent.mkdir(parents=True, exist_ok=True)
    staged_directory.mkdir()
    try:
        _write_staged_text(
            paths["geometry_table"],
            _csv_text(geometry_rows, tuple(geometry_rows[0])),
        )
        _write_staged_text(paths["value_table"], _csv_text(value_rows, tuple(value_rows[0])))
        _write_staged_text(
            paths["bootstrap_table"], _csv_text(bootstrap_rows, tuple(bootstrap_rows[0]))
        )
        _write_staged_text(paths["geometry_figure"], _geometry_svg(audit))
        _write_staged_text(paths["episode_figure"], _episode_svg(episodes))
        output_hashes = {
            name: {"path": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in paths.items()
            if name != "metadata"
        }
        metadata = {
            "schema_version": 1,
            "artifact_id": "run010-paper-artifacts-v1",
            "evidence_status": "REAL_DATA_OUTCOME_BLIND_DESCRIPTIVE_PRESENTATION",
            "source_audit_path": str(AUDIT_PATH.relative_to(ROOT)),
            "source_audit_sha256": INPUT_HASHES[AUDIT_PATH],
            "source_episode_path": str(EPISODE_PATH.relative_to(ROOT)),
            "source_episode_sha256": INPUT_HASHES[EPISODE_PATH],
            "outputs": output_hashes,
            "captions": {
                "geometry_figure": (
                    "Full-panel expanding-versus-rolling factor geometry under point-in-time and "
                    "matched-period latest ECB RTD values. Dashed lines are frozen failure "
                    "references."
                ),
                "episode_figure": (
                    "Persistent full-panel geometry-breach episodes under the primary 3/3 rule. "
                    "Intervals are descriptive and are not causal break estimates."
                ),
            },
            "boundaries": {
                "causal_revision_effect_claimed": False,
                "structural_break_inference_claimed": False,
                "decision_time_latest_vintage_use_allowed": False,
                "transmission_outcomes_accessed": False,
            },
        }
        _write_staged_text(paths["metadata"], json.dumps(metadata, indent=2, sort_keys=True) + "\n")
        staged_directory.replace(output_directory)
    except Exception:
        if staged_directory.exists():
            shutil.rmtree(staged_directory)
        raise
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT / "reports/paper/run011",
    )
    args = parser.parse_args()
    metadata = build(args.output_directory)
    print(json.dumps(metadata["outputs"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
