from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from app.warp.models import WarpRecord, WarpSummary


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS}
MAX_XLSX_SIZE = 5 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class StarRailStationImport:
    uid: str
    records: list[WarpRecord]
    summaries: list[WarpSummary]
    warnings: list[str]


def _sheet_type(name: str) -> str | None:
    normalized = name.casefold()
    if "colabora" in normalized and "cone" in normalized:
        return "22"
    if "colabora" in normalized and "personagem" in normalized:
        return "21"
    if normalized == "character event warp":
        return "11"
    if normalized == "light cone event warp":
        return "12"
    if "novato" in normalized:
        return "2"
    if "estelar" in normalized:
        return "1"
    return None


def _excel_time(value: str) -> str:
    date = datetime(1899, 12, 30) + timedelta(days=float(value))
    return date.strftime("%Y-%m-%d %H:%M:%S")


def _featured_name_for_record(
    banners: dict[str, list[tuple[float, float, str]]],
    banner_title: str,
    item_name: str,
    rank: int,
    excel_time: float,
) -> str:
    """Resolve o rate-up mesmo quando vários banners reutilizam o mesmo título."""
    definitions = banners.get(banner_title, [])
    active = [
        featured
        for starts_at, ends_at, featured in definitions
        if starts_at <= excel_time <= ends_at
    ]
    candidates = active or [featured for _, _, featured in definitions]
    if rank == 5:
        pulled = item_name.casefold().strip()
        for featured in candidates:
            if featured.casefold().strip() == pulled:
                return featured
    return candidates[0] if candidates else ""


class _WorkbookReader:
    def __init__(self, path: Path) -> None:
        self.archive = zipfile.ZipFile(path)
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            self.archive.read("xl/_rels/workbook.xml.rels")
        )
        relation_map = {
            item.attrib["Id"]: item.attrib["Target"] for item in relationships
        }
        self.sheets: dict[str, str] = {}
        for sheet in workbook.find("m:sheets", NS) or []:
            relation_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = relation_map[relation_id].lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            self.sheets[sheet.attrib["name"]] = target
        self.shared: list[str] = []
        if "xl/sharedStrings.xml" in self.archive.namelist():
            root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
            self.shared = [
                "".join(text.text or "" for text in item.iter(f"{{{MAIN_NS}}}t"))
                for item in root
            ]

    def close(self) -> None:
        self.archive.close()

    def rows(self, sheet_name: str) -> list[dict[str, str]]:
        root = ET.fromstring(self.archive.read(self.sheets[sheet_name]))
        result: list[dict[str, str]] = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values: dict[str, str] = {}
            for cell in row.findall("m:c", NS):
                value_node = cell.find("m:v", NS)
                value = "" if value_node is None else value_node.text or ""
                cell_type = cell.attrib.get("t")
                if cell_type == "s" and value:
                    value = self.shared[int(value)]
                elif cell_type == "inlineStr":
                    value = "".join(
                        text.text or ""
                        for text in cell.iter(f"{{{MAIN_NS}}}t")
                    )
                column = "".join(char for char in cell.attrib["r"] if char.isalpha())
                values[column] = value
            result.append(values)
        return result


def import_starrailstation_xlsx(path: Path, uid: str) -> StarRailStationImport:
    uid = uid.strip()
    if len(uid) != 9 or not uid.isdigit():
        raise ValueError("Defina uma UID principal de 9 números antes de importar o Excel.")
    if path.suffix.casefold() != ".xlsx":
        raise ValueError("Selecione um backup .xlsx do Star Rail Station.")
    try:
        file_size = path.stat().st_size
    except OSError as error:
        raise ValueError("Não foi possível acessar o arquivo XLSX selecionado.") from error
    if file_size > MAX_XLSX_SIZE:
        raise ValueError("O arquivo XLSX excede o limite de 5 MB.")

    reader = _WorkbookReader(path)
    try:
        banner_rows = reader.rows("Banners") if "Banners" in reader.sheets else []
        collaboration_names: dict[str, set[str]] = {"21": set(), "22": set()}
        collaboration_rows: dict[str, list[dict[str, str]]] = {"21": [], "22": []}
        banners_by_title: dict[str, list[tuple[float, float, str]]] = {}
        for row in banner_rows[1:]:
            if row.get("B") and row.get("C"):
                starts_at = float(row.get("J") or "-inf")
                ends_at = float(row.get("K") or "inf")
                banners_by_title.setdefault(row["B"], []).append(
                    (starts_at, ends_at, row["C"])
                )
            banner_type = row.get("A", "").casefold()
            if "colabora" not in banner_type:
                continue
            kind = "22" if "cone" in banner_type else "21"
            collaboration_names[kind].add(row.get("B", ""))
            if int(float(row.get("D") or 0)) > 0:
                collaboration_rows[kind].append(row)

        records: list[WarpRecord] = []
        for sheet_name in reader.sheets:
            default_type = _sheet_type(sheet_name)
            if default_type is None:
                continue
            rows = reader.rows(sheet_name)
            for row in rows[1:]:
                developer = row.get("G", "").split(",")
                if len(developer) != 4 or not row.get("E"):
                    continue
                item_id, _manual, _banner_id, record_id = developer
                gacha_type = default_type
                banner_name = row.get("F", "")
                if default_type == "11" and banner_name in collaboration_names["21"]:
                    gacha_type = "21"
                elif default_type == "12" and banner_name in collaboration_names["22"]:
                    gacha_type = "22"
                rank = len(row.get("B", ""))
                if rank not in (3, 4, 5) or not record_id:
                    continue
                records.append(WarpRecord(
                    id=record_id,
                    uid=uid,
                    gacha_type=gacha_type,
                    item_id=item_id,
                    name=row.get("C", "Item desconhecido"),
                    item_type="Character" if int(item_id) < 20000 else "Light Cone",
                    rank_type=rank,
                    time=_excel_time(row["E"]),
                    banner_title=banner_name,
                    banner_id=_banner_id.strip(),
                    featured_name=_featured_name_for_record(
                        banners_by_title,
                        banner_name,
                        row.get("C", "Item desconhecido"),
                        rank,
                        float(row["E"]),
                    ),
                ))

        summaries: list[WarpSummary] = []
        warnings: list[str] = []
        detailed_counts = {
            kind: sum(record.gacha_type == kind for record in records)
            for kind in ("21", "22")
        }
        for kind in ("21", "22"):
            rows = collaboration_rows[kind]
            if not rows or detailed_counts[kind]:
                continue
            total = sum(int(float(row.get("D") or 0)) for row in rows)
            five_count = sum(int(float(row.get("E") or 0)) for row in rows)
            four_count = sum(int(float(row.get("H") or 0)) for row in rows)
            populated = [row for row in rows if int(float(row.get("E") or 0)) > 0]
            if len(populated) != 1 or int(float(populated[0].get("E") or 0)) != 1:
                warnings.append(
                    f"O resumo do banner {kind} não permite reconstruir o pity exato."
                )
                continue
            row = populated[0]
            featured_pity = round(float(row.get("G") or 0))
            last_four_position = round(float(row.get("I") or 0) * four_count)
            item_name = row.get("C", "5★ de colaboração")
            item_ids = {
                "Saber": "1014",
                "Archer": "1015",
                "Rin Tohsaka": "1508",
                "Gilgamesh": "1509",
                "Uma Coroação Sem Gratidão": "23045",
                "O Inferno Onde os Ideais Ardem": "23046",
                "Estrelas Cintilantes": "23061",
                "Eu Sou Como Tu Me Vês": "23062",
            }
            item_id = item_ids.get(item_name, "")
            if not item_id:
                warnings.append(f"Imagem não identificada para {item_name}.")
            summaries.append(WarpSummary(
                uid=uid,
                gacha_type=kind,
                total=total,
                five_star_count=five_count,
                four_star_count=four_count,
                five_star_pity=max(total - featured_pity, 0),
                four_star_pity=max(total - last_four_position, 0),
                featured_item_id=item_id,
                featured_item_name=item_name,
                featured_pity=featured_pity,
                featured_item_type="Character" if kind == "21" else "Light Cone",
            ))
        return StarRailStationImport(uid, records, summaries, warnings)
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise ValueError("O arquivo não é um backup válido do Star Rail Station.") from error
    finally:
        reader.close()
