"""Extrai os perfis públicos de pontuação do código-fonte do HSR Optimizer.

Uso:
    python scripts/sync_fribbels_weights.py CAMINHO_DO_REPOSITORIO_FRIBBELS
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


STAT_KEYS = {
    "HP": "HPDelta",
    "ATK": "AttackDelta",
    "DEF": "DefenceDelta",
    "HP_P": "HPAddedRatio",
    "ATK_P": "AttackAddedRatio",
    "DEF_P": "DefenceAddedRatio",
    "SPD": "SpeedDelta",
    "CR": "CriticalChance",
    "CD": "CriticalDamage",
    "EHR": "StatusProbability",
    "RES": "StatusResistance",
    "BE": "BreakDamageAddedRatio",
    "Physical_DMG": "PhysicalAddedRatio",
    "Fire_DMG": "FireAddedRatio",
    "Ice_DMG": "IceAddedRatio",
    "Lightning_DMG": "ThunderAddedRatio",
    "Wind_DMG": "WindAddedRatio",
    "Quantum_DMG": "QuantumAddedRatio",
    "Imaginary_DMG": "ImaginaryAddedRatio",
    "ERR": "SPRatio",
    "OHB": "HealRatio",
}

PART_KEYS = {
    "Head": "HEAD",
    "Hands": "HAND",
    "Body": "BODY",
    "Feet": "FOOT",
    "PlanarSphere": "ORBIT",
    "LinkRope": "ROPE",
}


def balanced_block(text: str, marker: str, start: int = 0) -> str:
    marker_at = text.find(marker, start)
    if marker_at < 0:
        return ""
    brace = text.find("{", marker_at)
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    return ""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Informe o caminho do repositório fribbels/hsr-optimizer.")
    repository = Path(sys.argv[1]).resolve()
    source = repository / "src" / "lib" / "conditionals" / "character"
    if not source.is_dir():
        raise SystemExit(f"Pasta de personagens não encontrada: {source}")

    characters: dict[str, dict[str, object]] = {}
    for path in source.rglob("*.ts"):
        text = path.read_text(encoding="utf-8")
        for export in re.finditer(r"export const (\w+): CharacterConfig = \{", text):
            export_block = balanced_block(text, export.group(0), export.start())
            id_match = re.search(r"\bid:\s*['\"]([^'\"]+)['\"]", export_block)
            if not id_match:
                continue

            before = text[:export.start()]
            scoring_at = before.rfind("const scoring = (): ScoringMetadata => ({")
            if scoring_at < 0:
                continue
            scoring = balanced_block(text, "const scoring = (): ScoringMetadata => ({", scoring_at)
            stats = balanced_block(scoring, "stats:")
            parts = balanced_block(scoring, "parts:")

            weights: dict[str, float] = {}
            for stat, value in re.findall(r"\[Stats\.(\w+)\]:\s*([0-9.]+)", stats):
                if stat in STAT_KEYS:
                    weights[STAT_KEYS[stat]] = float(value)

            main_stats: dict[str, list[str]] = {}
            for part, values in re.findall(
                r"\[Parts\.(\w+)\]:\s*\[([^\]]*)\]", parts, flags=re.DOTALL
            ):
                if part not in PART_KEYS:
                    continue
                main_stats[PART_KEYS[part]] = [
                    STAT_KEYS[stat]
                    for stat in re.findall(r"Stats\.(\w+)", values)
                    if stat in STAT_KEYS
                ]

            if weights:
                characters[id_match.group(1)] = {
                    "name": export.group(1),
                    "weights": weights,
                    "main_stats": main_stats,
                }

    head = (repository / ".git" / "HEAD").read_text(encoding="ascii").strip()
    if head.startswith("ref: "):
        commit = (repository / ".git" / head[5:]).read_text(encoding="ascii").strip()
    else:
        commit = head
    output = Path(__file__).resolve().parents[1] / "app" / "benchmark" / "fribbels_weights.json"
    payload = {
        "source": "https://github.com/fribbels/hsr-optimizer",
        "commit": commit,
        "characters": dict(sorted(characters.items())),
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(characters)} perfis gravados em {output}")


if __name__ == "__main__":
    main()
