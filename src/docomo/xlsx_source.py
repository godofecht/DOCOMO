"""Minimal, strict OOXML reader for externally sourced project-estimation workbooks.

Reads values and metadata without evaluating formulas or executing macros.
Only .xlsx ZIP containers with worksheet XML are accepted. Ingestion refuses
source-formula cells, external links and invalid/corrupt structures rather than
silently interpreting cached spreadsheet calculations as measured human effort.
"""
from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Mapping
from pathlib import Path
from xml.etree import ElementTree as ET

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKGREL = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
NS = {"s": MAIN, "r": REL}
CELL_RE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")
MAX_ARCHIVE_BYTES = 20_000_000
MAX_EXPANDED_BYTES = 60_000_000
MAX_SHEETS = 50
MAX_ROWS = 20_000


def _safe_archive(file: Path) -> tuple[zipfile.ZipFile, str]:
    if file.suffix.lower() != ".xlsx" or not file.is_file():
        raise ValueError("source must be an existing original .xlsx file")
    if file.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("source workbook exceeds size limit")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    z = zipfile.ZipFile(file, "r")
    infos = z.infolist()
    total = 0
    for info in infos:
        name = info.filename
        if name.startswith("/") or "\\" in name or any(c == ".." for c in name.split("/")):
            z.close()
            raise ValueError("invalid OOXML archive path")
        if info.flag_bits & 1:
            z.close()
            raise ValueError("encrypted OOXML archives are not supported")
        total += info.file_size
        if total > MAX_EXPANDED_BYTES:
            z.close()
            raise ValueError("OOXML archive exceeds expanded-content limit")
        if ("externalLink" in name or name.lower().endswith("vbaproject.bin")
                or name.endswith(".bin") and name.startswith("xl/")):
            z.close()
            raise ValueError("external links or executable workbook components are not allowed")
    return z, digest


def _text(element: ET.Element) -> str:
    return "".join(x.text or "" for x in element.iter(f"{{{MAIN}}}t"))


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        raw = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    return [_text(x) for x in root.findall(f"{{{MAIN}}}si")]


def _sheet_paths(archive: zipfile.ZipFile) -> list[dict]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {}
    for relation in relationships.findall(f"{{{PKGREL}}}Relationship"):
        if relation.get("TargetMode", "").lower() == "external":
            raise ValueError("external workbook relationships are forbidden")
        if relation.get("Type") == DOCREL:
            target = relation.get("Target", "")
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            segments = []
            for part in target.split("/"):
                if part == "..":
                    if not segments:
                        raise ValueError("invalid sheet relationship path")
                    segments.pop()
                elif part and part != ".":
                    segments.append(part)
            target = "/".join(segments)
            if target not in archive.namelist():
                raise ValueError("missing worksheet file in OOXML archive")
            targets[relation.get("Id")] = target
    sheets = workbook.find(f"{{{MAIN}}}sheets")
    if sheets is None or len(sheets) == 0 or len(sheets) > MAX_SHEETS:
        raise ValueError("workbook must contain 1..50 sheets")
    found = []
    names = set()
    for entry in sheets:
        name = entry.get("name", "")
        rel = entry.get(f"{{{REL}}}id")
        if not name or name in names or rel not in targets:
            raise ValueError("invalid or duplicate worksheet name/relationship")
        names.add(name)
        found.append({"name": name, "state": entry.get("state", "visible"),
                      "path": targets[rel]})
    return found


def _cell_value(cell: ET.Element, strings: list[str]) -> tuple[object, bool]:
    formula = cell.find(f"{{{MAIN}}}f") is not None
    if formula:
        return None, True
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        node = cell.find(f"{{{MAIN}}}is")
        return (_text(node) if node is not None else ""), False
    v = cell.find(f"{{{MAIN}}}v")
    if v is None:
        return None, False
    raw = v.text or ""
    if kind == "s":
        try:
            idx = int(raw)
            return strings[idx] if idx >= 0 else None, False
        except (ValueError, IndexError) as error:
            raise ValueError("invalid shared string reference") from error
    if kind in ("str", "e", "d"):
        if kind == "e":
            raise ValueError(f"spreadsheet contains Excel error cell: {raw}")
        return raw, False
    if kind == "b":
        if raw not in ("0", "1"):
            raise ValueError("invalid boolean workbook cell")
        return raw == "1", False
    if kind in ("n", ""):
        try:
            return float(raw), False
        except ValueError as error:
            raise ValueError("invalid numeric worksheet cell") from error
    raise ValueError(f"unsupported OOXML cell type: {kind}")


def read_xlsx_sheet(file: str | Path, *, sheet_name: str) -> dict:
    """Read one visible Excel worksheet; return literal values and formula flags."""
    path = Path(file)
    archive, digest = _safe_archive(path)
    try:
        sheets = _sheet_paths(archive)
        selected = next((s for s in sheets if s["name"] == sheet_name), None)
        if selected is None:
            raise ValueError(f"requested worksheet not found: {sheet_name}")
        if selected["state"] != "visible":
            raise ValueError("scoring a hidden or veryHidden worksheet is forbidden")
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(selected["path"]))
        data = root.find(f"{{{MAIN}}}sheetData")
        if data is None:
            raise ValueError("worksheet is missing sheetData")
        values: dict[int, dict[int, object]] = {}
        formulas: set[tuple[int, int]] = set()
        occupied = set()
        for row in data.findall(f"{{{MAIN}}}row"):
            rowid = int(row.get("r", "0"))
            if not 1 <= rowid <= MAX_ROWS or rowid in values:
                raise ValueError("invalid or duplicate spreadsheet row")
            fields = {}
            for cell in row.findall(f"{{{MAIN}}}c"):
                ref = cell.get("r", "")
                match = CELL_RE.fullmatch(ref)
                if match is None or int(match.group(2)) != rowid:
                    raise ValueError("invalid/mismatched Excel cell coordinate")
                colname = match.group(1)
                col = 0
                for letter in colname:
                    col = col * 26 + ord(letter) - ord("A") + 1
                if col > 16384 or (rowid, col) in occupied:
                    raise ValueError("invalid or duplicate Excel cell")
                occupied.add((rowid, col))
                result, is_formula = _cell_value(cell, strings)
                if is_formula:
                    formulas.add((rowid, col))
                fields[col] = result
            values[rowid] = fields
        return {
            "source_sha256": digest,
            "sheet": sheet_name,
            "visible_sheets": [s["name"] for s in sheets if s["state"] == "visible"],
            "hidden_sheets": [s["name"] for s in sheets if s["state"] != "visible"],
            "rows": values,
            "formula_cells": formulas,
            "row_count": len(values),
        }
    except (KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        raise ValueError("invalid or malformed OOXML workbook structure") from error
    finally:
        archive.close()
