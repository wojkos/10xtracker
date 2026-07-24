from pathlib import Path

from pydantic import BaseModel


class RoadmapCorrelation(BaseModel):
    roadmap_id: str
    outcome: str


def _extract_table_lines(text: str) -> list[str]:
    heading_index = text.find("## At a glance")
    if heading_index == -1:
        return []

    lines = text[heading_index:].splitlines()[1:]
    table_lines: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            started = True
            table_lines.append(stripped)
        elif started:
            break
    return table_lines


def get_roadmap_correlations(context_dir: Path) -> dict[str, RoadmapCorrelation]:
    try:
        roadmap_path = context_dir / "foundation" / "roadmap.md"
        if not roadmap_path.is_file():
            return {}

        text = roadmap_path.read_text(encoding="utf-8")
        table_lines = _extract_table_lines(text)
        if len(table_lines) < 2:
            return {}

        correlations: dict[str, RoadmapCorrelation] = {}
        for line in table_lines[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            roadmap_id, change_id, outcome = cells[0], cells[1], cells[2]
            correlations[change_id] = RoadmapCorrelation(roadmap_id=roadmap_id, outcome=outcome)
        return correlations
    except OSError:
        return {}
