from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "app" / "benchmark" / "fribbels_teams.json"


def balanced(text: str, start: int, opening: str, closing: str) -> str:
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "'\"`":
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ""


def exported_configs(files: list[Path], config_type: str) -> dict[str, dict[str, str]]:
    configs: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        rf"export\s+const\s+(\w+)\s*:\s*{config_type}\s*=\s*\{{"
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        local_ids = dict(re.findall(r"\bconst\s+(\w+)(?:\s*:[^=]+)?\s*=\s*'([^']+)'", text))
        for match in pattern.finditer(text):
            block = balanced(text, match.end() - 1, "{", "}")
            identifier = re.search(r"\bid\s*:\s*(?:'([^']+)'|(\w+))", block)
            if not identifier:
                continue
            identifier_value = identifier.group(1) or local_ids.get(identifier.group(2), "")
            if not identifier_value:
                continue
            default = re.search(
                r"\bdefaultLightCone\s*:\s*(?:(\w+)\.(?:id|defaultLightCone)|'([^']+)')",
                block,
            )
            configs[match.group(1)] = {
                "id": identifier_value,
                "default": (default.group(1) or default.group(2)) if default else "",
                "file": str(path),
            }
    return configs


def yaml_names(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    sections: dict[str, dict[str, str]] = {"Characters": {}, "Lightcones": {}}
    section = ""
    current_id = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line in ("Characters:", "Lightcones:"):
            section = raw_line[:-1]
            current_id = ""
            continue
        identifier = re.match(r'^  (?:(?:"([^\"]+)")|([^:\s]+)):\s*$', raw_line)
        if identifier and section:
            current_id = identifier.group(1) or identifier.group(2)
            continue
        name = re.match(r"^    Name:\s*(.+?)\s*$", raw_line)
        if name and section and current_id:
            value = name.group(1)
            if value.startswith(('"', "'")) and value.endswith(value[0]):
                value = value[1:-1]
            sections[section][current_id] = value.replace("⚰️ ", "")
    return sections["Characters"], sections["Lightcones"]


def fallback_name(alias: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", alias).replace(" B1", "")


def localized_name(names: dict[str, str], identifier: str, alias: str) -> str:
    base_id = re.match(r"\d+", identifier)
    return names.get(identifier) or names.get(base_id.group(0) if base_id else "") or fallback_name(alias)


def resolve_light_cone(
    expression_alias: str,
    character_alias: str,
    characters: dict[str, dict[str, str]],
    light_cones: dict[str, dict[str, str]],
) -> tuple[str, str]:
    alias = expression_alias
    if character_alias and expression_alias == "defaultLightCone":
        alias = characters.get(character_alias, {}).get("default", "")
    elif character_alias and expression_alias == character_alias:
        alias = characters.get(character_alias, {}).get("default", "")
    config = light_cones.get(alias, {})
    return config.get("id", alias), alias


def extract_team(
    path: Path,
    characters: dict[str, dict[str, str]],
    light_cones: dict[str, dict[str, str]],
    character_names: dict[str, str],
    light_cone_names: dict[str, str],
) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    simulation = re.search(r"\bconst\s+simulation\w*\s*=", text)
    search_from = simulation.start() if simulation else 0
    team_match = re.search(r"\bteammates\s*:\s*\[", text[search_from:])
    if not team_match:
        return []
    bracket_start = search_from + team_match.end() - 1
    team_block = balanced(text, bracket_start, "[", "]")
    members: list[dict[str, object]] = []
    for object_match in re.finditer(r"\{([^{}]+)\}", team_block, re.DOTALL):
        block = object_match.group(1)
        character = re.search(r"characterId\s*:\s*(?:(\w+)\.id|'([^']+)')", block)
        cone = re.search(
            r"lightCone\s*:\s*(?:(\w+)\.(id|defaultLightCone)|'([^']+)')",
            block,
        )
        eidolon = re.search(r"characterEidolon\s*:\s*(\d+)", block)
        superimposition = re.search(r"lightConeSuperimposition\s*:\s*(\d+)", block)
        if not (character and cone and eidolon and superimposition):
            continue
        character_alias = character.group(1) or ""
        character_id = character.group(2) or characters.get(character_alias, {}).get("id", character_alias)
        if cone.group(3):
            cone_id, cone_alias = cone.group(3), cone.group(3)
        elif cone.group(2) == "defaultLightCone":
            cone_alias = characters.get(cone.group(1), {}).get("default", "")
            cone_id = light_cones.get(cone_alias, {}).get("id", cone_alias)
        else:
            cone_alias = cone.group(1)
            cone_id = light_cones.get(cone_alias, {}).get("id", cone_alias)
        members.append({
            "character_id": character_id,
            "name": localized_name(character_names, character_id, character_alias),
            "eidolon": int(eidolon.group(1)),
            "light_cone_id": cone_id,
            "light_cone": light_cone_names.get(cone_id, fallback_name(cone_alias)),
            "superimposition": int(superimposition.group(1)),
        })
    return members[:3]


def source_commit(source: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build(source: Path) -> dict[str, object]:
    character_dir = source / "src" / "lib" / "conditionals" / "character"
    light_cone_dir = source / "src" / "lib" / "conditionals" / "lightcone"
    locale = source / "public" / "locales" / "pt_BR" / "gameData.yaml"
    character_files = list(character_dir.rglob("*.ts"))
    cone_files = list(light_cone_dir.rglob("*.ts"))
    characters = exported_configs(character_files, "CharacterConfig")
    light_cones = exported_configs(cone_files, "LightConeConfig")
    character_names, light_cone_names = yaml_names(locale)

    teams: dict[str, object] = {}
    for path in character_files:
        members = extract_team(
            path, characters, light_cones, character_names, light_cone_names
        )
        if len(members) != 3:
            continue
        local_configs = [
            (alias, config) for alias, config in characters.items()
            if config["file"] == str(path) and re.fullmatch(r"\d+", config["id"])
        ]
        for alias, config in local_configs:
            character_id = config["id"]
            teams[character_id] = {
                "name": f"Time padrão Fribbels · {localized_name(character_names, character_id, alias)}",
                "members": members,
            }
    return {
        "source": "fribbels/hsr-optimizer",
        "source_commit": source_commit(source),
        "teams": dict(sorted(teams.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa os times padrão do Fribbels.")
    parser.add_argument("source", type=Path, help="Pasta do repositório hsr-optimizer")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build(args.source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(payload['teams'])} times exportados para {args.output}")


if __name__ == "__main__":
    main()
