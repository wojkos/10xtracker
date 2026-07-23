import re
from pathlib import Path

from pydantic import BaseModel

PHASE_HEADING_RE = re.compile(r"^### Phase (\d+):")
CHECKBOX_RE = re.compile(r"^- \[([ xX])\]")


class PhaseProgress(BaseModel):
    phase_number: int
    done: int
    total: int


def _split_into_phase_blocks(progress_section: str) -> list[tuple[int, list[str]]]:
    blocks: list[tuple[int, list[str]]] = []
    current_number: int | None = None
    current_lines: list[str] = []

    for line in progress_section.splitlines():
        match = PHASE_HEADING_RE.match(line)
        if match:
            if current_number is not None:
                blocks.append((current_number, current_lines))
            current_number = int(match.group(1))
            current_lines = []
        elif current_number is not None:
            current_lines.append(line)

    if current_number is not None:
        blocks.append((current_number, current_lines))

    return blocks


def _count_checkboxes(lines: list[str]) -> tuple[int, int]:
    done = 0
    total = 0
    for line in lines:
        match = CHECKBOX_RE.match(line.strip())
        if not match:
            continue
        total += 1
        if match.group(1) in ("x", "X"):
            done += 1
    return done, total


def get_phase_progress(change_dir: Path) -> PhaseProgress | None:
    try:
        plan_path = change_dir / "plan.md"
        if not plan_path.is_file():
            return None

        text = plan_path.read_text(encoding="utf-8")
        heading_index = text.find("## Progress")
        if heading_index == -1:
            return None

        progress_section = text[heading_index:]
        blocks = _split_into_phase_blocks(progress_section)

        candidates: list[tuple[int, int, int]] = []
        for phase_number, lines in blocks:
            done, total = _count_checkboxes(lines)
            if total == 0:
                continue
            candidates.append((phase_number, done, total))

        if not candidates:
            return None

        for phase_number, done, total in candidates:
            if done < total:
                return PhaseProgress(phase_number=phase_number, done=done, total=total)

        last_phase_number, last_done, last_total = candidates[-1]
        return PhaseProgress(phase_number=last_phase_number, done=last_done, total=last_total)
    except OSError:
        return None
