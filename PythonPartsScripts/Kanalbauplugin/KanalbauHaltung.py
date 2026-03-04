"""
KanalbauHaltung.py – Allplan PythonPart für eine Kanalhaltung (2024)

Erstellt eine vollständige Kanalhaltung bestehend aus:
  - Startschacht (Schachtring, Konus, Aufbau, Sohlplatte)
  - Rohrleitung  (hohles Rohr mit Gefälle)
  - Stationierung (Texte entlang der Rohrachse)
  - Endschacht   (Schachtring, Konus, Aufbau, Sohlplatte)

Parametereingabe über 4-seitige Palette (KanalbauHaltung.pyp).
Rohr- und Schachtdimensionen können aus CSV-Dateien geladen werden.
Interaktive Handles an Rohrsohle (Start/Ende) und Schachtdeckeln.

Koordinatenursprung:
  (0, 0, 0) = Rohrsohle (Invert) am Startschacht
  X-Achse   = horizontale Rohrlängsachse
  Z-Achse   = vertikal nach oben

CSV-Dateien:
  csv/Rohrdimensionen.csv    – DN, Wandstaerke_mm, Material, Innenrauheit
  csv/Schachtdimensionen.csv – DN_Schacht, Wandstaerke_mm, KonusDN_oben,
                               KonusHoehe_mm, SohlplatteStaerke_mm

Die CSV-Dateien liegen zwei Verzeichnisebenen über diesem Skript
(../../csv/ relativ zu PythonPartsScripts/Kanalbauplugin/).
"""

import csv
import math
import os
import sys

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_BasisElements as AllplanBasisElements

from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult
from HandleDirection import HandleDirection
from HandleParameterData import HandleParameterData
from HandleParameterType import HandleParameterType
from HandleProperties import HandleProperties

# Lokale Geometrie-Module
from geometry.schacht import create_schacht, deckel_position
from geometry.rohr import create_rohr, rohr_end_point
from geometry.stationierung import create_stationierung


# ---------------------------------------------------------------------------
# Pflicht-API-Funktionen
# ---------------------------------------------------------------------------

def check_allplan_version(build_ele: BuildingElement, version: float) -> bool:
    """Unterstützt Allplan 2024 und neuer."""
    return version >= 2024.0


# ---------------------------------------------------------------------------
# CSV-Hilfsfunktionen
# ---------------------------------------------------------------------------

def _csv_dir() -> str:
    """Gibt den absoluten Pfad zum csv/-Verzeichnis zurück."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "..", "..", "csv")


def _load_rohrdimensionen() -> dict:
    """
    Lädt Rohrdimensionen aus CSV.
    Rückgabe: {str(DN): {'Wandstaerke_mm': str, 'Material': str, ...}}
    Bei Fehler: leeres Dict (Fallback auf .pyp-Defaults).
    """
    data: dict = {}
    try:
        path = os.path.join(_csv_dir(), "Rohrdimensionen.csv")
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                data[row["DN"].strip()] = row
    except Exception:
        pass
    return data


def _load_schachtdimensionen() -> dict:
    """
    Lädt Schachtdimensionen aus CSV.
    Rückgabe: {str(DN_Schacht): {'Wandstaerke_mm': str, ...}}
    Bei Fehler: leeres Dict.
    """
    data: dict = {}
    try:
        path = os.path.join(_csv_dir(), "Schachtdimensionen.csv")
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                data[row["DN_Schacht"].strip()] = row
    except Exception:
        pass
    return data


def _csv_float(data: dict, dn_key: str, field: str, fallback: float) -> float:
    """
    Liest einen Float-Wert aus dem CSV-Dict; gibt fallback bei fehlendem Eintrag.
    """
    row = data.get(str(dn_key))
    if row is None:
        return fallback
    try:
        return float(row[field])
    except (KeyError, ValueError):
        return fallback


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def create_element(build_ele: BuildingElement, doc) -> CreateElementResult:
    """
    Erstellt die gesamte Kanalhaltung (Startschacht + Rohr + Endschacht)
    und die zugehörigen Handles.
    """
    # ------------------------------------------------------------------
    # CSV-Daten laden
    # ------------------------------------------------------------------
    rohr_csv   = _load_rohrdimensionen()
    schacht_csv = _load_schachtdimensionen()

    # ------------------------------------------------------------------
    # Parameter aus der Palette lesen
    # ------------------------------------------------------------------

    # Seite 1 – Übersicht
    haltungs_name        = build_ele.HaltungsName.value
    startschacht_name    = build_ele.StartschachtName.value
    endschacht_name      = build_ele.EndschachtName.value
    haltungslaenge       = build_ele.Haltungslaenge.value       # mm
    gefalle              = build_ele.Gefalle.value              # %
    stat_abstand         = build_ele.StationierungsAbstand.value  # mm
    stat_offset_m        = build_ele.StationierungsOffset.value   # m

    # Seite 2 – Startschacht
    start_dn             = build_ele.StartSchachtDN.value       # mm (int)
    start_wand           = build_ele.StartWandstaerke.value
    start_tiefe          = build_ele.StartSchachtTiefe.value
    start_mit_konus      = build_ele.StartMitKonus.value
    start_konus_h        = build_ele.StartKonusHoehe.value
    start_konus_dn_oben  = build_ele.StartKonusDN_oben.value
    start_aufbau_h       = build_ele.StartAufbauHoehe.value
    start_aufbau_dn      = build_ele.StartAufbauDN.value
    start_sohlplatte     = build_ele.StartSohlplatteH.value

    # CSV-Overrides für Startschacht (nur wenn DN in CSV vorhanden)
    start_wand      = _csv_float(schacht_csv, start_dn, "Wandstaerke_mm",  start_wand)
    start_konus_dn_oben = _csv_float(schacht_csv, start_dn, "KonusDN_oben",    start_konus_dn_oben)
    start_konus_h   = _csv_float(schacht_csv, start_dn, "KonusHoehe_mm",   start_konus_h)
    start_sohlplatte = _csv_float(schacht_csv, start_dn, "SohlplatteStaerke_mm", start_sohlplatte)

    # Seite 3 – Rohrleitung
    rohr_dn              = build_ele.RohrDN.value               # mm (int)
    rohr_wand            = build_ele.RohrWandstaerke.value
    # rohr_material      = build_ele.RohrMaterial.value         # String, nur für Attribute
    mit_stationierung    = build_ele.RohrMitStationierung.value
    stat_text_h          = build_ele.StationierungsTextHoehe.value
    stat_text_offset     = build_ele.StationierungsTextOffset.value

    # CSV-Overrides für Rohrleitung
    rohr_wand = _csv_float(rohr_csv, rohr_dn, "Wandstaerke_mm", rohr_wand)

    # Seite 4 – Endschacht
    end_dn               = build_ele.EndSchachtDN.value
    end_wand             = build_ele.EndWandstaerke.value
    end_tiefe            = build_ele.EndSchachtTiefe.value
    end_mit_konus        = build_ele.EndMitKonus.value
    end_konus_h          = build_ele.EndKonusHoehe.value
    end_konus_dn_oben    = build_ele.EndKonusDN_oben.value
    end_aufbau_h         = build_ele.EndAufbauHoehe.value
    end_aufbau_dn        = build_ele.EndAufbauDN.value
    end_sohlplatte       = build_ele.EndSohlplatteH.value

    # CSV-Overrides für Endschacht
    end_wand         = _csv_float(schacht_csv, end_dn, "Wandstaerke_mm",      end_wand)
    end_konus_dn_oben = _csv_float(schacht_csv, end_dn, "KonusDN_oben",       end_konus_dn_oben)
    end_konus_h      = _csv_float(schacht_csv, end_dn, "KonusHoehe_mm",       end_konus_h)
    end_sohlplatte   = _csv_float(schacht_csv, end_dn, "SohlplatteStaerke_mm", end_sohlplatte)

    # ------------------------------------------------------------------
    # Abgeleitete Geometriewerte
    # ------------------------------------------------------------------
    rohr_r_aussen = rohr_dn / 2.0
    rohr_r_innen  = max(rohr_r_aussen - rohr_wand, 10.0)

    # Koordinatensystem-Ursprung: Rohrsohle Startschacht = (0, 0, 0)
    # Rohrachse liegt in der XZ-Ebene (Y=0)
    start_sohle = AllplanGeo.Point3D(0, 0, 0)
    end_sohle   = rohr_end_point(start_sohle, haltungslaenge, gefalle)

    # ------------------------------------------------------------------
    # Element-Eigenschaften
    # ------------------------------------------------------------------
    common_props = AllplanBaseElements.CommonProperties()
    common_props.GetGlobalProperties()

    all_elements: list = []

    # ------------------------------------------------------------------
    # 1. STARTSCHACHT
    # ------------------------------------------------------------------
    start_elems = create_schacht(
        origin          = start_sohle,
        schacht_dm      = float(start_dn),
        wandstaerke     = start_wand,
        tiefe           = start_tiefe,
        mit_konus       = start_mit_konus,
        konus_hoehe     = start_konus_h,
        konus_dn_oben   = start_konus_dn_oben,
        aufbau_hoehe    = start_aufbau_h,
        aufbau_dn       = start_aufbau_dn,
        sohlplatte_h    = start_sohlplatte,
        common_props    = common_props
    )
    all_elements.extend(start_elems)

    # ------------------------------------------------------------------
    # 2. ROHRLEITUNG
    # ------------------------------------------------------------------
    rohr_elems = create_rohr(
        start_pt     = start_sohle,
        end_pt       = end_sohle,
        r_aussen     = rohr_r_aussen,
        r_innen      = rohr_r_innen,
        common_props = common_props
    )
    all_elements.extend(rohr_elems)

    # ------------------------------------------------------------------
    # 3. STATIONIERUNG
    # ------------------------------------------------------------------
    if mit_stationierung and stat_abstand > 0:
        stat_elems = create_stationierung(
            start_pt       = start_sohle,
            end_pt         = end_sohle,
            abstand        = stat_abstand,
            text_hoehe     = stat_text_h,
            text_offset    = stat_text_offset,
            start_offset_m = stat_offset_m,
            common_props   = common_props
        )
        all_elements.extend(stat_elems)

    # ------------------------------------------------------------------
    # 4. ENDSCHACHT
    # ------------------------------------------------------------------
    end_elems = create_schacht(
        origin          = end_sohle,
        schacht_dm      = float(end_dn),
        wandstaerke     = end_wand,
        tiefe           = end_tiefe,
        mit_konus       = end_mit_konus,
        konus_hoehe     = end_konus_h,
        konus_dn_oben   = end_konus_dn_oben,
        aufbau_hoehe    = end_aufbau_h,
        aufbau_dn       = end_aufbau_dn,
        sohlplatte_h    = end_sohlplatte,
        common_props    = common_props
    )
    all_elements.extend(end_elems)

    # ------------------------------------------------------------------
    # 5. HANDLES
    # ------------------------------------------------------------------
    handles: list = []

    # Handle 1: Rohrsohle Startschacht (Z-Richtung → steuert Gefälle)
    handle_start_sohle = HandleProperties(
        "start_sohle",
        start_sohle,                                # handle_point
        AllplanGeo.Point3D(0, 0, -start_sohlplatte),  # ref_point (Unterkante Sohlplatte)
        [HandleParameterData("Gefalle", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR
    )
    handles.append(handle_start_sohle)

    # Handle 2: Rohrsohle Endschacht (Z-Richtung → steuert Gefälle; X → Haltungslänge)
    handle_end_sohle = HandleProperties(
        "end_sohle",
        end_sohle,
        start_sohle,
        [
            HandleParameterData("Haltungslaenge", HandleParameterType.X_DISTANCE, False),
            HandleParameterData("Gefalle",        HandleParameterType.Z_DISTANCE, False),
        ],
        HandleDirection.XZ_DIR
    )
    handles.append(handle_end_sohle)

    # Handle 3: Schachtdeckel Startschacht (Z → steuert Schachttiefe)
    pt_deckel_start = deckel_position(
        origin       = start_sohle,
        tiefe        = start_tiefe,
        mit_konus    = start_mit_konus,
        konus_hoehe  = start_konus_h,
        aufbau_hoehe = start_aufbau_h,
        sohlplatte_h = start_sohlplatte
    )
    handle_deckel_start = HandleProperties(
        "start_deckel",
        pt_deckel_start,
        start_sohle,
        [HandleParameterData("StartSchachtTiefe", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR
    )
    handles.append(handle_deckel_start)

    # Handle 4: Schachtdeckel Endschacht (Z → steuert Schachttiefe)
    pt_deckel_end = deckel_position(
        origin       = end_sohle,
        tiefe        = end_tiefe,
        mit_konus    = end_mit_konus,
        konus_hoehe  = end_konus_h,
        aufbau_hoehe = end_aufbau_h,
        sohlplatte_h = end_sohlplatte
    )
    handle_deckel_end = HandleProperties(
        "end_deckel",
        pt_deckel_end,
        end_sohle,
        [HandleParameterData("EndSchachtTiefe", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR
    )
    handles.append(handle_deckel_end)

    # ------------------------------------------------------------------
    # 6. Ergebnis
    # ------------------------------------------------------------------
    return CreateElementResult(elements=all_elements, handles=handles)


def create_preview(build_ele: BuildingElement, doc) -> CreateElementResult:
    """
    Vorschau-Geometrie – identisch zur finalen Geometrie.
    Wird beim Bewegen der Maus in der Palette angezeigt.
    """
    return create_element(build_ele, doc)
