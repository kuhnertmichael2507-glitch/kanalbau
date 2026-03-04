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

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_BasisElements as AllplanBasisElements

from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult
from HandleDirection import HandleDirection
from HandleParameterData import HandleParameterData
from HandleParameterType import HandleParameterType
from HandleProperties import HandleProperties


# ---------------------------------------------------------------------------
# Pflicht-API-Funktionen
# ---------------------------------------------------------------------------

def check_allplan_version(build_ele: BuildingElement, version: float) -> bool:
    """Unterstützt Allplan 2024 und neuer."""
    return float(version) >= 2024.0


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
# Rohr-Geometrie
# ---------------------------------------------------------------------------

def _perp_vector(nx: float, ny: float, nz: float) -> AllplanGeo.Vector3D:
    """
    Berechnet einen Einheitsvektor senkrecht zu (nx, ny, nz).
    Wird als X-Achse für AxisPlacement3D(Point3D, xvector, zvector) benötigt.
    """
    if abs(nz) < 0.9:
        px, py, pz = ny, -nx, 0.0
    else:
        px, py, pz = 0.0, nz, -ny

    length = math.sqrt(px * px + py * py + pz * pz)
    if length < 1e-9:
        return AllplanGeo.Vector3D(1.0, 0.0, 0.0)
    return AllplanGeo.Vector3D(px / length, py / length, pz / length)


def _create_rohr(
        start_pt: AllplanGeo.Point3D,
        end_pt:   AllplanGeo.Point3D,
        r_aussen: float,
        r_innen:  float,
        common_props) -> list:
    """
    Erstellt ein hohles Rohr von start_pt nach end_pt.

    Parameter
    ---------
    start_pt     : 3D-Punkt der Rohrsohle am Startschacht
    end_pt       : 3D-Punkt der Rohrsohle am Endschacht
    r_aussen     : Außenradius (mm)
    r_innen      : Innenradius (mm)
    common_props : AllplanBaseElements.CommonProperties

    Rückgabe
    --------
    Liste [ModelElement3D]
    """
    r_innen = max(r_innen, 10.0)

    dx = end_pt.X - start_pt.X
    dy = end_pt.Y - start_pt.Y
    dz = end_pt.Z - start_pt.Z
    laenge = math.sqrt(dx * dx + dy * dy + dz * dz)

    if laenge < 1.0:
        return []

    nx, ny, nz = dx / laenge, dy / laenge, dz / laenge

    z_vec = AllplanGeo.Vector3D(nx, ny, nz)
    x_vec = _perp_vector(nx, ny, nz)

    # AxisPlacement3D(Point3D, xvector, zvector)
    axis = AllplanGeo.AxisPlacement3D(start_pt, x_vec, z_vec)

    outer = AllplanGeo.BRep3D.CreateCylinder(axis, r_aussen, laenge, True, True)
    inner = AllplanGeo.BRep3D.CreateCylinder(axis, r_innen,  laenge, True, True)

    err, hollow = AllplanGeo.MakeSubtraction(outer, inner)
    geo = hollow if (not err and not hollow.IsEmpty()) else outer

    return [AllplanBasisElements.ModelElement3D(common_props, geo)]


def _rohr_end_point(start_pt: AllplanGeo.Point3D,
                    haltungslaenge: float,
                    gefalle_pct: float) -> AllplanGeo.Point3D:
    """
    Berechnet den Endpunkt der Rohrsohle aus Startpunkt, Länge und Gefälle.

    Das Rohr liegt in der XZ-Ebene (Y=konstant).
    Gefälle in % → Neigungswinkel alpha = arctan(gefalle_pct / 100).
    Der Endpunkt liegt auf der geneigten Achse in Entfernung haltungslaenge.

    Parameter
    ---------
    start_pt      : Startpunkt (Rohrsohle Startschacht)
    haltungslaenge: Horizontale Rohrlänge (mm)
    gefalle_pct   : Gefälle in Prozent (positiv = Rohr fällt in X-Richtung ab)
    """
    alpha = math.atan(gefalle_pct / 100.0)
    dx = haltungslaenge * math.cos(alpha)
    dz = -haltungslaenge * math.sin(alpha)   # negativ = abfallend

    return AllplanGeo.Point3D(
        start_pt.X + dx,
        start_pt.Y,
        start_pt.Z + dz
    )


# ---------------------------------------------------------------------------
# Schacht-Geometrie
# ---------------------------------------------------------------------------

def _hollow_cylinder(origin: AllplanGeo.Point3D,
                     r_aussen: float,
                     r_innen: float,
                     hoehe: float,
                     common_props) -> AllplanBasisElements.ModelElement3D:
    """
    Erstellt einen Hohlzylinder (BRep3D) mit senkrechter Achse (+Z).
    """
    r_innen = max(r_innen, 10.0)
    axis = AllplanGeo.AxisPlacement3D(origin)

    outer = AllplanGeo.BRep3D.CreateCylinder(axis, r_aussen, hoehe, True, True)
    inner = AllplanGeo.BRep3D.CreateCylinder(axis, r_innen,  hoehe, True, True)

    err, hollow = AllplanGeo.MakeSubtraction(outer, inner)
    geo = hollow if (not err and not hollow.IsEmpty()) else outer
    return AllplanBasisElements.ModelElement3D(common_props, geo)


def _frustum(origin: AllplanGeo.Point3D,
             r_unten: float,
             r_oben: float,
             hoehe: float,
             wandstaerke: float,
             common_props) -> AllplanBasisElements.ModelElement3D | None:
    """
    Erstellt einen hohlen Kegelstumpf (Frustum) mit senkrechter Achse (+Z).

    Methode:
      1. Vollständigen Kegel erzeugen.
      2. Mit Clipping-Quader über z=origin.Z+hoehe abschneiden.
      3. Innenform erzeugen und subtrahieren.
    """
    r_innen_unten = max(r_unten - wandstaerke, 10.0)
    r_innen_oben  = max(r_oben  - wandstaerke, 10.0)

    def _make_frustum_brep(r_bottom: float, r_top: float) -> AllplanGeo.BRep3D | None:
        if abs(r_bottom - r_top) < 0.1:
            axis = AllplanGeo.AxisPlacement3D(origin)
            return AllplanGeo.BRep3D.CreateCylinder(axis, r_bottom, hoehe, True, True)

        apex_h = hoehe * r_bottom / (r_bottom - r_top)
        apex_pt = AllplanGeo.Point3D(origin.X, origin.Y, origin.Z + apex_h)

        cone3d = AllplanGeo.Cone3D(
            AllplanGeo.AxisPlacement3D(origin),
            r_bottom,
            0.0,
            apex_pt
        )
        full_cone = AllplanGeo.BRep3D.CreateCone(cone3d, True)

        z_cut = origin.Z + hoehe
        clip_origin = AllplanGeo.Point3D(origin.X - 20000, origin.Y - 20000, z_cut)
        clip = AllplanGeo.BRep3D.CreateCuboid(
            AllplanGeo.AxisPlacement3D(clip_origin),
            40000.0, 40000.0, apex_h + 5000.0
        )
        err, stumpf = AllplanGeo.MakeSubtraction(full_cone, clip)
        return stumpf if (not err and not stumpf.IsEmpty()) else full_cone

    outer_stumpf = _make_frustum_brep(r_unten, r_oben)
    inner_stumpf = _make_frustum_brep(r_innen_unten, r_innen_oben)

    if outer_stumpf is None:
        return None

    if inner_stumpf is not None:
        err2, hollow_cone = AllplanGeo.MakeSubtraction(outer_stumpf, inner_stumpf)
        geo = hollow_cone if (not err2 and not hollow_cone.IsEmpty()) else outer_stumpf
    else:
        geo = outer_stumpf

    return AllplanBasisElements.ModelElement3D(common_props, geo)


def _create_schacht(
        origin: AllplanGeo.Point3D,
        schacht_dm: float,
        wandstaerke: float,
        tiefe: float,
        mit_konus: bool,
        konus_hoehe: float,
        konus_dn_oben: float,
        aufbau_hoehe: float,
        aufbau_dn: float,
        sohlplatte_h: float,
        common_props) -> list:
    """
    Erstellt einen kompletten Kanalschacht als Liste von ModelElement3D.

    Geometrischer Aufbau (von unten nach oben):
      1. Sohlplatte   – Cuboid, zentriert, Dicke nach unten (-Z)
      2. Schachtring  – Hohlzylinder
      3. Konus        – Kegelstumpf (optional)
      4. Aufbau/Hals  – Kleiner Hohlzylinder

    Parameter
    ---------
    origin        : Punkt an der Rohrsohle des Zuflussrohres
    schacht_dm    : Aussendurchmesser Schachtring (mm)
    wandstaerke   : Wandstärke (mm)
    tiefe         : Nutztiefe Schachtring (mm)
    mit_konus     : True = Konus vorhanden
    konus_hoehe   : Höhe des Konus (mm)
    konus_dn_oben : Aussendurchmesser oben am Konus (mm)
    aufbau_hoehe  : Höhe des Halsrings (mm)
    aufbau_dn     : Aussendurchmesser Aufbau (mm)
    sohlplatte_h  : Stärke der Sohlplatte (mm), ragt nach unten
    common_props  : AllplanBaseElements.CommonProperties
    """
    elements: list = []

    r_aussen = schacht_dm / 2.0
    r_innen  = max(r_aussen - wandstaerke, 10.0)

    z0 = origin.Z - sohlplatte_h
    z1 = origin.Z
    z2 = z1 + tiefe
    z3 = z2 + (konus_hoehe if mit_konus else 0.0)

    # 1. SOHLPLATTE
    sohlplatte_origin = AllplanGeo.Point3D(
        origin.X - r_aussen,
        origin.Y - r_aussen,
        z0
    )
    sohlplatte_geo = AllplanGeo.BRep3D.CreateCuboid(
        AllplanGeo.AxisPlacement3D(sohlplatte_origin),
        schacht_dm,
        schacht_dm,
        sohlplatte_h
    )
    elements.append(AllplanBasisElements.ModelElement3D(common_props, sohlplatte_geo))

    # 2. SCHACHTRING
    ring_origin = AllplanGeo.Point3D(origin.X, origin.Y, z1)
    ring_ele = _hollow_cylinder(ring_origin, r_aussen, r_innen, tiefe, common_props)
    if ring_ele is not None:
        elements.append(ring_ele)

    # 3. KONUS (optional)
    if mit_konus and konus_hoehe > 0:
        konus_r_unten = r_aussen
        konus_r_oben  = konus_dn_oben / 2.0
        konus_origin  = AllplanGeo.Point3D(origin.X, origin.Y, z2)

        konus_ele = _frustum(
            konus_origin,
            konus_r_unten,
            konus_r_oben,
            konus_hoehe,
            wandstaerke,
            common_props
        )
        if konus_ele is not None:
            elements.append(konus_ele)

    # 4. AUFBAU / HALSRING
    if aufbau_hoehe > 0:
        aufbau_r_aussen = aufbau_dn / 2.0
        aufbau_r_innen  = max(aufbau_r_aussen - wandstaerke, 10.0)
        aufbau_origin   = AllplanGeo.Point3D(origin.X, origin.Y, z3)

        aufbau_ele = _hollow_cylinder(
            aufbau_origin, aufbau_r_aussen, aufbau_r_innen, aufbau_hoehe, common_props
        )
        if aufbau_ele is not None:
            elements.append(aufbau_ele)

    return elements


def _deckel_position(origin: AllplanGeo.Point3D,
                     tiefe: float,
                     mit_konus: bool,
                     konus_hoehe: float,
                     aufbau_hoehe: float,
                     sohlplatte_h: float) -> AllplanGeo.Point3D:
    """
    Berechnet die Z-Position des Schachtdeckels (Oberkante Aufbau).
    Wird für Handle-Platzierung verwendet.
    """
    z_deckel = (origin.Z
                + tiefe
                + (konus_hoehe if mit_konus else 0.0)
                + aufbau_hoehe)
    return AllplanGeo.Point3D(origin.X, origin.Y, z_deckel)


# ---------------------------------------------------------------------------
# Stationierungs-Geometrie
# ---------------------------------------------------------------------------

def _format_station(meter: float, start_offset_m: float = 0.0) -> str:
    """
    Formatiert einen Stationswert als "km+m"-String.
    Beispiel: 1234.5 → "1+234"
    """
    total_m = int(round(meter + start_offset_m))
    km   = total_m // 1000
    rest = total_m  % 1000
    return f"{km}+{rest:03d}"


def _create_stationierung(
        start_pt: AllplanGeo.Point3D,
        end_pt:   AllplanGeo.Point3D,
        abstand: float,
        text_hoehe: float,
        text_offset: float,
        start_offset_m: float,
        common_props) -> list:
    """
    Erzeugt Stationierungstexte entlang der Rohrachse.

    Parameter
    ---------
    start_pt       : Rohrsohle Startschacht
    end_pt         : Rohrsohle Endschacht
    abstand        : Abstand zwischen Stationierungspunkten (mm)
    text_hoehe     : Schriftgröße (mm)
    text_offset    : Versatz des Textes senkrecht zur Achse (mm)
    start_offset_m : Startstation in Metern (für Nummerierung)
    common_props   : AllplanBaseElements.CommonProperties

    Rückgabe
    --------
    Liste von TextElement-Objekten
    """
    elements: list = []

    dx = end_pt.X - start_pt.X
    dy = end_pt.Y - start_pt.Y
    dz = end_pt.Z - start_pt.Z
    laenge = math.sqrt(dx * dx + dy * dy + dz * dz)

    if laenge < 1.0 or abstand < 1.0:
        return elements

    # Einheitsvektor entlang Rohrachse
    ux = dx / laenge
    uy = dy / laenge
    uz = dz / laenge

    # Senkrechter Quervektor in der Horizontalebene (für Textversatz)
    # Normalvektor in XY: (-uy, ux, 0) – dreht 90° nach links
    qx = -uy
    qy =  ux

    anzahl = int(laenge / abstand)

    # Textausrichtungswinkel (Drehung im Grundriss, Grad)
    winkel_grad = math.degrees(math.atan2(dy, dx))

    for i in range(anzahl + 1):
        s = i * abstand
        if s > laenge + 0.1:
            break

        # Punkt auf der Rohrachse
        pt_achse = AllplanGeo.Point3D(
            start_pt.X + ux * s,
            start_pt.Y + uy * s,
            start_pt.Z + uz * s
        )

        # Textposition (Point2D – TextElement ist 2D)
        pt_text = AllplanGeo.Point2D(
            pt_achse.X + qx * text_offset,
            pt_achse.Y + qy * text_offset
        )

        # Stationstext (Meter)
        meter_wert = s / 1000.0
        text_str = _format_station(meter_wert, start_offset_m)

        # TextElement erstellen
        text_props = AllplanBasisElements.TextProperties()
        text_props.Height        = text_hoehe
        text_props.Width         = text_hoehe * 0.7
        text_props.RotationAngle = math.radians(winkel_grad)

        text_ele = AllplanBasisElements.TextElement(
            common_props,
            text_props,
            text_str,
            pt_text
        )
        elements.append(text_ele)

    return elements


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
    rohr_csv    = _load_rohrdimensionen()
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
    start_dn             = build_ele.StartSchachtDN.value
    start_wand           = build_ele.StartWandstaerke.value
    start_tiefe          = build_ele.StartSchachtTiefe.value
    start_mit_konus      = build_ele.StartMitKonus.value
    start_konus_h        = build_ele.StartKonusHoehe.value
    start_konus_dn_oben  = build_ele.StartKonusDN_oben.value
    start_aufbau_h       = build_ele.StartAufbauHoehe.value
    start_aufbau_dn      = build_ele.StartAufbauDN.value
    start_sohlplatte     = build_ele.StartSohlplatteH.value

    # CSV-Overrides für Startschacht
    start_wand          = _csv_float(schacht_csv, start_dn, "Wandstaerke_mm",       start_wand)
    start_konus_dn_oben = _csv_float(schacht_csv, start_dn, "KonusDN_oben",         start_konus_dn_oben)
    start_konus_h       = _csv_float(schacht_csv, start_dn, "KonusHoehe_mm",        start_konus_h)
    start_sohlplatte    = _csv_float(schacht_csv, start_dn, "SohlplatteStaerke_mm", start_sohlplatte)

    # Seite 3 – Rohrleitung
    rohr_dn              = build_ele.RohrDN.value
    rohr_wand            = build_ele.RohrWandstaerke.value
    mit_stationierung    = build_ele.RohrMitStationierung.value
    stat_text_h          = build_ele.StationierungsTextHoehe.value
    stat_text_offset     = build_ele.StationierungsTextOffset.value

    # CSV-Override für Rohrleitung
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
    end_wand            = _csv_float(schacht_csv, end_dn, "Wandstaerke_mm",       end_wand)
    end_konus_dn_oben   = _csv_float(schacht_csv, end_dn, "KonusDN_oben",         end_konus_dn_oben)
    end_konus_h         = _csv_float(schacht_csv, end_dn, "KonusHoehe_mm",        end_konus_h)
    end_sohlplatte      = _csv_float(schacht_csv, end_dn, "SohlplatteStaerke_mm", end_sohlplatte)

    # ------------------------------------------------------------------
    # Abgeleitete Geometriewerte
    # ------------------------------------------------------------------
    rohr_r_aussen = rohr_dn / 2.0
    rohr_r_innen  = max(rohr_r_aussen - rohr_wand, 10.0)

    # Koordinatenursprung: Rohrsohle Startschacht = (0, 0, 0)
    start_sohle = AllplanGeo.Point3D(0, 0, 0)
    end_sohle   = _rohr_end_point(start_sohle, haltungslaenge, gefalle)

    # ------------------------------------------------------------------
    # Element-Eigenschaften
    # ------------------------------------------------------------------
    common_props = AllplanBaseElements.CommonProperties()
    common_props.GetGlobalProperties()

    all_elements: list = []

    # ------------------------------------------------------------------
    # 1. STARTSCHACHT
    # ------------------------------------------------------------------
    start_elems = _create_schacht(
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
    rohr_elems = _create_rohr(
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
        stat_elems = _create_stationierung(
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
    end_elems = _create_schacht(
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

    # Handle 1: Rohrsohle Startschacht (Z → steuert Gefälle)
    handle_start_sohle = HandleProperties(
        "start_sohle",
        start_sohle,
        AllplanGeo.Point3D(0, 0, -start_sohlplatte),
        [HandleParameterData("Gefalle", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR
    )
    handles.append(handle_start_sohle)

    # Handle 2: Rohrsohle Endschacht (X → Haltungslänge; Z → Gefälle)
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
    pt_deckel_start = _deckel_position(
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
    pt_deckel_end = _deckel_position(
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
