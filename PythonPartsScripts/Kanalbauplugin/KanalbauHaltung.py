"""
KanalbauHaltung.py – Allplan PythonPart für eine Kanalhaltung (2024)

Erstellt eine vollständige Kanalhaltung bestehend aus:
  - Startschacht (Schachtring, Konus, Aufbau, Sohlplatte)
  - Rohrleitung  (hohles Rohr + 3D-Linie Rohrsohle)
  - Stationierung (Texte entlang der Rohrachse)
  - Endschacht   (Schachtring, Konus, Aufbau, Sohlplatte)

Interaktor-Workflow:
  1. Klick: Rohrsohle Startschacht (3D-Punkt im Modell)
  2. Klick: Rohrsohle Endschacht  (3D-Punkt im Modell)
  → Haltung wird zwischen diesen Punkten erzeugt.

Die Koordinaten werden in versteckten Parametern (StartX/Y/Z, DeltaX/Y/Z)
gespeichert, damit das PythonPart nach der Platzierung editierbar bleibt.

CSV-Dateien:
  csv/Rohrdimensionen.csv    – DN, Wandstaerke_mm, Material, Innenrauheit
  csv/Schachtdimensionen.csv – DN_Schacht, Wandstaerke_mm, KonusDN_oben,
                               KonusHoehe_mm, SohlplatteStaerke_mm
"""

import csv
import math
import os

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_BasisElements as AllplanBasisElements
import NemAll_Python_IFW_Input as AllplanIFWInput

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
# Interaktor  (2-Punkt-Eingabe: Rohrsohle Start → Ende)
# ---------------------------------------------------------------------------

def create_interactor(coord_input, pyp_path, str_table_service, build_ele_list, doc):
    """Factory-Funktion – wird von Allplan beim Start des Interaktors aufgerufen."""
    return Interactor(coord_input, pyp_path, str_table_service, build_ele_list, doc)


class Interactor:
    """
    Interaktor für die 2-Punkt-Eingabe der Rohrsohle.

    Ablauf
    ------
    1. Klick → Startpunkt (StartX/Y/Z)
    2. Klick → Endpunkt   (DeltaX/Y/Z = End − Start)
    → Interaktor gibt False zurück, Allplan ruft create_element() auf.

    Vorschau
    --------
    Zwischen Klick 1 und Klick 2 wird eine 3D-Linie vom Startpunkt zur
    aktuellen Mausposition als Preview gezeichnet.
    """

    def __init__(self, coord_input, pyp_path, str_table_service, build_ele_list, doc):
        self.coord_input  = coord_input
        self.doc          = doc
        self.build_ele    = build_ele_list[0]
        self.first_pt     = None          # AllplanGeo.Point3D – nach Klick 1 gesetzt
        self.cur_pt       = AllplanGeo.Point3D()
        self.input_mode   = 0             # 0 = wartet auf Klick 1, 1 = wartet auf Klick 2

        prompt = AllplanIFWInput.InputStringConvert("Startpunkt Rohrsohle eingeben")
        coord_input.InitFirstPointInput(prompt)

    # ------------------------------------------------------------------
    def on_preview_draw(self):
        """Zeichnet eine Vorschau-Linie während der Mausbewegung."""
        if self.input_mode == 1 and self.first_pt is not None:
            cur = self.coord_input.GetCurrentPoint().GetPoint()
            if cur is None:
                return
            line = AllplanGeo.Line3D(self.first_pt, cur)
            props = AllplanBaseElements.CommonProperties()
            props.GetGlobalProperties()
            preview = [AllplanBasisElements.ModelElement3D(props, line)]
            AllplanBaseElements.DrawElementPreview(
                self.doc,
                AllplanGeo.Matrix3D(),
                preview,
                False,
                None
            )

    # ------------------------------------------------------------------
    def on_mouse_leave(self):
        pass

    # ------------------------------------------------------------------
    def process_mouse_msg(self, mouse_msg, pnt, msg_info) -> bool:
        """
        Verarbeitet Maus-Nachrichten.

        Rückgabe
        --------
        True  = weiter auf Eingabe warten
        False = Eingabe abgeschlossen (Allplan ruft create_element auf)
        """
        self.cur_pt = pnt

        if self.input_mode == 0:
            # --- Warten auf Startpunkt ---
            if not AllplanIFWInput.CoordInput.IsMouseMove(mouse_msg):
                self.first_pt = AllplanGeo.Point3D(pnt.X, pnt.Y, pnt.Z)
                self.build_ele.StartX.value = pnt.X
                self.build_ele.StartY.value = pnt.Y
                self.build_ele.StartZ.value = pnt.Z
                self.input_mode = 1
                prompt = AllplanIFWInput.InputStringConvert("Endpunkt Rohrsohle eingeben")
                self.coord_input.InitNextPointInput(prompt)
        else:
            # --- Warten auf Endpunkt ---
            if not AllplanIFWInput.CoordInput.IsMouseMove(mouse_msg):
                if self.first_pt is not None:
                    self.build_ele.DeltaX.value = pnt.X - self.first_pt.X
                    self.build_ele.DeltaY.value = pnt.Y - self.first_pt.Y
                    self.build_ele.DeltaZ.value = pnt.Z - self.first_pt.Z
                return False   # Eingabe fertig → create_element wird aufgerufen

        return True

    # ------------------------------------------------------------------
    def on_cancel_function(self):
        pass

    def on_create_element(self):
        pass


# ---------------------------------------------------------------------------
# CSV-Hilfsfunktionen
# ---------------------------------------------------------------------------

def _csv_dir() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "..", "..", "csv")


def _load_rohrdimensionen() -> dict:
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
    """Einheitsvektor senkrecht zu (nx, ny, nz) – X-Achse für AxisPlacement3D."""
    if abs(nz) < 0.9:
        px, py, pz = ny, -nx, 0.0
    else:
        px, py, pz = 0.0, nz, -ny
    length = math.sqrt(px * px + py * py + pz * pz)
    if length < 1e-9:
        return AllplanGeo.Vector3D(1.0, 0.0, 0.0)
    return AllplanGeo.Vector3D(px / length, py / length, pz / length)


def _create_rohr(start_pt, end_pt, r_aussen, r_innen, common_props) -> list:
    """Hohles Rohr entlang beliebiger 3D-Achse."""
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
    axis  = AllplanGeo.AxisPlacement3D(start_pt, x_vec, z_vec)
    outer = AllplanGeo.BRep3D.CreateCylinder(axis, r_aussen, laenge, True, True)
    inner = AllplanGeo.BRep3D.CreateCylinder(axis, r_innen,  laenge, True, True)
    err, hollow = AllplanGeo.MakeSubtraction(outer, inner)
    geo = hollow if (not err and not hollow.IsEmpty()) else outer
    return [AllplanBasisElements.ModelElement3D(common_props, geo)]


# ---------------------------------------------------------------------------
# Schacht-Geometrie
# ---------------------------------------------------------------------------

def _hollow_cylinder(origin, r_aussen, r_innen, hoehe, common_props):
    r_innen = max(r_innen, 10.0)
    axis  = AllplanGeo.AxisPlacement3D(origin)
    outer = AllplanGeo.BRep3D.CreateCylinder(axis, r_aussen, hoehe, True, True)
    inner = AllplanGeo.BRep3D.CreateCylinder(axis, r_innen,  hoehe, True, True)
    err, hollow = AllplanGeo.MakeSubtraction(outer, inner)
    geo = hollow if (not err and not hollow.IsEmpty()) else outer
    return AllplanBasisElements.ModelElement3D(common_props, geo)


def _frustum(origin, r_unten, r_oben, hoehe, wandstaerke, common_props):
    r_innen_unten = max(r_unten - wandstaerke, 10.0)
    r_innen_oben  = max(r_oben  - wandstaerke, 10.0)

    def _make_frustum_brep(r_bottom, r_top):
        if abs(r_bottom - r_top) < 0.1:
            axis = AllplanGeo.AxisPlacement3D(origin)
            return AllplanGeo.BRep3D.CreateCylinder(axis, r_bottom, hoehe, True, True)
        apex_h  = hoehe * r_bottom / (r_bottom - r_top)
        apex_pt = AllplanGeo.Point3D(origin.X, origin.Y, origin.Z + apex_h)
        cone3d  = AllplanGeo.Cone3D(AllplanGeo.AxisPlacement3D(origin), r_bottom, 0.0, apex_pt)
        full_cone = AllplanGeo.BRep3D.CreateCone(cone3d, True)
        z_cut = origin.Z + hoehe
        clip_origin = AllplanGeo.Point3D(origin.X - 20000, origin.Y - 20000, z_cut)
        clip = AllplanGeo.BRep3D.CreateCuboid(
            AllplanGeo.AxisPlacement3D(clip_origin), 40000.0, 40000.0, apex_h + 5000.0)
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


def _create_schacht(origin, schacht_dm, wandstaerke, tiefe, mit_konus,
                    konus_hoehe, konus_dn_oben, aufbau_hoehe, aufbau_dn,
                    sohlplatte_h, common_props) -> list:
    elements: list = []
    r_aussen = schacht_dm / 2.0
    r_innen  = max(r_aussen - wandstaerke, 10.0)

    z0 = origin.Z - sohlplatte_h
    z1 = origin.Z
    z2 = z1 + tiefe
    z3 = z2 + (konus_hoehe if mit_konus else 0.0)

    # Sohlplatte
    sol_origin = AllplanGeo.Point3D(origin.X - r_aussen, origin.Y - r_aussen, z0)
    sol_geo    = AllplanGeo.BRep3D.CreateCuboid(
        AllplanGeo.AxisPlacement3D(sol_origin), schacht_dm, schacht_dm, sohlplatte_h)
    elements.append(AllplanBasisElements.ModelElement3D(common_props, sol_geo))

    # Schachtring
    ring_ele = _hollow_cylinder(
        AllplanGeo.Point3D(origin.X, origin.Y, z1), r_aussen, r_innen, tiefe, common_props)
    if ring_ele is not None:
        elements.append(ring_ele)

    # Konus
    if mit_konus and konus_hoehe > 0:
        konus_ele = _frustum(
            AllplanGeo.Point3D(origin.X, origin.Y, z2),
            r_aussen, konus_dn_oben / 2.0, konus_hoehe, wandstaerke, common_props)
        if konus_ele is not None:
            elements.append(konus_ele)

    # Aufbau / Halsring
    if aufbau_hoehe > 0:
        aufbau_r_a = aufbau_dn / 2.0
        aufbau_r_i = max(aufbau_r_a - wandstaerke, 10.0)
        aufbau_ele = _hollow_cylinder(
            AllplanGeo.Point3D(origin.X, origin.Y, z3),
            aufbau_r_a, aufbau_r_i, aufbau_hoehe, common_props)
        if aufbau_ele is not None:
            elements.append(aufbau_ele)

    return elements


def _deckel_position(origin, tiefe, mit_konus, konus_hoehe,
                     aufbau_hoehe, sohlplatte_h) -> AllplanGeo.Point3D:
    z = origin.Z + tiefe + (konus_hoehe if mit_konus else 0.0) + aufbau_hoehe
    return AllplanGeo.Point3D(origin.X, origin.Y, z)


# ---------------------------------------------------------------------------
# Stationierungs-Geometrie
# ---------------------------------------------------------------------------

def _format_station(meter: float, start_offset_m: float = 0.0) -> str:
    total_m = int(round(meter + start_offset_m))
    km   = total_m // 1000
    rest = total_m  % 1000
    return f"{km}+{rest:03d}"


def _create_stationierung(start_pt, end_pt, abstand, text_hoehe,
                          text_offset, start_offset_m, common_props) -> list:
    elements: list = []
    dx = end_pt.X - start_pt.X
    dy = end_pt.Y - start_pt.Y
    dz = end_pt.Z - start_pt.Z
    laenge = math.sqrt(dx * dx + dy * dy + dz * dz)
    if laenge < 1.0 or abstand < 1.0:
        return elements

    ux = dx / laenge
    uy = dy / laenge
    uz = dz / laenge
    qx = -uy
    qy =  ux

    anzahl     = int(laenge / abstand)
    winkel_rad = math.atan2(dy, dx)

    for i in range(anzahl + 1):
        s = i * abstand
        if s > laenge + 0.1:
            break
        pt_achse = AllplanGeo.Point3D(
            start_pt.X + ux * s,
            start_pt.Y + uy * s,
            start_pt.Z + uz * s)
        pt_text  = AllplanGeo.Point2D(
            pt_achse.X + qx * text_offset,
            pt_achse.Y + qy * text_offset)
        text_str = _format_station(s / 1000.0, start_offset_m)

        text_props = AllplanBasisElements.TextProperties()
        text_props.Height        = text_hoehe
        text_props.Width         = text_hoehe * 0.7
        text_props.RotationAngle = winkel_rad

        elements.append(AllplanBasisElements.TextElement(
            common_props, text_props, text_str, pt_text))

    return elements


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def create_element(build_ele: BuildingElement, doc) -> CreateElementResult:
    """
    Erstellt die gesamte Kanalhaltung aus den gespeicherten Koordinaten
    (StartX/Y/Z + DeltaX/Y/Z) und den Palettenparametern.
    """
    # --- CSV laden ---
    rohr_csv    = _load_rohrdimensionen()
    schacht_csv = _load_schachtdimensionen()

    # --- Koordinaten aus versteckten Parametern ---
    start_sohle = AllplanGeo.Point3D(
        build_ele.StartX.value,
        build_ele.StartY.value,
        build_ele.StartZ.value)
    end_sohle = AllplanGeo.Point3D(
        build_ele.StartX.value + build_ele.DeltaX.value,
        build_ele.StartY.value + build_ele.DeltaY.value,
        build_ele.StartZ.value + build_ele.DeltaZ.value)

    # --- Seite 1 – Übersicht ---
    stat_abstand    = build_ele.StationierungsAbstand.value
    stat_offset_m   = build_ele.StationierungsOffset.value

    # --- Seite 2 – Startschacht ---
    start_dn            = build_ele.StartSchachtDN.value
    start_wand          = build_ele.StartWandstaerke.value
    start_tiefe         = build_ele.StartSchachtTiefe.value
    start_mit_konus     = build_ele.StartMitKonus.value
    start_konus_h       = build_ele.StartKonusHoehe.value
    start_konus_dn_oben = build_ele.StartKonusDN_oben.value
    start_aufbau_h      = build_ele.StartAufbauHoehe.value
    start_aufbau_dn     = build_ele.StartAufbauDN.value
    start_sohlplatte    = build_ele.StartSohlplatteH.value

    start_wand          = _csv_float(schacht_csv, start_dn, "Wandstaerke_mm",       start_wand)
    start_konus_dn_oben = _csv_float(schacht_csv, start_dn, "KonusDN_oben",         start_konus_dn_oben)
    start_konus_h       = _csv_float(schacht_csv, start_dn, "KonusHoehe_mm",        start_konus_h)
    start_sohlplatte    = _csv_float(schacht_csv, start_dn, "SohlplatteStaerke_mm", start_sohlplatte)

    # --- Seite 3 – Rohrleitung ---
    rohr_dn           = build_ele.RohrDN.value
    rohr_wand         = build_ele.RohrWandstaerke.value
    mit_stationierung = build_ele.RohrMitStationierung.value
    stat_text_h       = build_ele.StationierungsTextHoehe.value
    stat_text_offset  = build_ele.StationierungsTextOffset.value
    rohr_wand         = _csv_float(rohr_csv, rohr_dn, "Wandstaerke_mm", rohr_wand)

    # --- Seite 4 – Endschacht ---
    end_dn              = build_ele.EndSchachtDN.value
    end_wand            = build_ele.EndWandstaerke.value
    end_tiefe           = build_ele.EndSchachtTiefe.value
    end_mit_konus       = build_ele.EndMitKonus.value
    end_konus_h         = build_ele.EndKonusHoehe.value
    end_konus_dn_oben   = build_ele.EndKonusDN_oben.value
    end_aufbau_h        = build_ele.EndAufbauHoehe.value
    end_aufbau_dn       = build_ele.EndAufbauDN.value
    end_sohlplatte      = build_ele.EndSohlplatteH.value

    end_wand          = _csv_float(schacht_csv, end_dn, "Wandstaerke_mm",       end_wand)
    end_konus_dn_oben = _csv_float(schacht_csv, end_dn, "KonusDN_oben",         end_konus_dn_oben)
    end_konus_h       = _csv_float(schacht_csv, end_dn, "KonusHoehe_mm",        end_konus_h)
    end_sohlplatte    = _csv_float(schacht_csv, end_dn, "SohlplatteStaerke_mm", end_sohlplatte)

    # --- Geometriewerte ---
    rohr_r_aussen = rohr_dn / 2.0
    rohr_r_innen  = max(rohr_r_aussen - rohr_wand, 10.0)

    # --- CommonProperties ---
    common_props = AllplanBaseElements.CommonProperties()
    common_props.GetGlobalProperties()

    all_elements: list = []

    # 1. ROHRSOHLE als 3D-Linie
    rohrsohle_line = AllplanGeo.Line3D(start_sohle, end_sohle)
    all_elements.append(AllplanBasisElements.ModelElement3D(common_props, rohrsohle_line))

    # 2. STARTSCHACHT
    all_elements.extend(_create_schacht(
        origin=start_sohle, schacht_dm=float(start_dn), wandstaerke=start_wand,
        tiefe=start_tiefe, mit_konus=start_mit_konus, konus_hoehe=start_konus_h,
        konus_dn_oben=start_konus_dn_oben, aufbau_hoehe=start_aufbau_h,
        aufbau_dn=start_aufbau_dn, sohlplatte_h=start_sohlplatte,
        common_props=common_props))

    # 3. ROHRLEITUNG (Hohlzylinder)
    all_elements.extend(_create_rohr(
        start_pt=start_sohle, end_pt=end_sohle,
        r_aussen=rohr_r_aussen, r_innen=rohr_r_innen,
        common_props=common_props))

    # 4. STATIONIERUNG
    if mit_stationierung and stat_abstand > 0:
        all_elements.extend(_create_stationierung(
            start_pt=start_sohle, end_pt=end_sohle, abstand=stat_abstand,
            text_hoehe=stat_text_h, text_offset=stat_text_offset,
            start_offset_m=stat_offset_m, common_props=common_props))

    # 5. ENDSCHACHT
    all_elements.extend(_create_schacht(
        origin=end_sohle, schacht_dm=float(end_dn), wandstaerke=end_wand,
        tiefe=end_tiefe, mit_konus=end_mit_konus, konus_hoehe=end_konus_h,
        konus_dn_oben=end_konus_dn_oben, aufbau_hoehe=end_aufbau_h,
        aufbau_dn=end_aufbau_dn, sohlplatte_h=end_sohlplatte,
        common_props=common_props))

    # ------------------------------------------------------------------
    # HANDLES
    # ------------------------------------------------------------------
    handles: list = []

    # Handle 1: Endpunkt der Rohrsohle (XZ-Richtung → DeltaX + DeltaZ)
    # Verschieben des Endschachts in Längs- und Höhenrichtung
    handle_end = HandleProperties(
        "end_sohle",
        end_sohle,
        start_sohle,
        [
            HandleParameterData("DeltaX", HandleParameterType.X_DISTANCE, False),
            HandleParameterData("DeltaZ", HandleParameterType.Z_DISTANCE, False),
        ],
        HandleDirection.XZ_DIR
    )
    handles.append(handle_end)

    # Handle 2: Deckel Startschacht (Z → StartSchachtTiefe)
    pt_deckel_start = _deckel_position(
        start_sohle, start_tiefe, start_mit_konus, start_konus_h,
        start_aufbau_h, start_sohlplatte)
    handles.append(HandleProperties(
        "start_deckel",
        pt_deckel_start,
        start_sohle,
        [HandleParameterData("StartSchachtTiefe", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR))

    # Handle 3: Deckel Endschacht (Z → EndSchachtTiefe)
    pt_deckel_end = _deckel_position(
        end_sohle, end_tiefe, end_mit_konus, end_konus_h,
        end_aufbau_h, end_sohlplatte)
    handles.append(HandleProperties(
        "end_deckel",
        pt_deckel_end,
        end_sohle,
        [HandleParameterData("EndSchachtTiefe", HandleParameterType.Z_DISTANCE, False)],
        HandleDirection.Z_DIR))

    return CreateElementResult(elements=all_elements, handles=handles)


def create_preview(build_ele: BuildingElement, doc) -> CreateElementResult:
    """Vorschau – identisch zur finalen Geometrie."""
    return create_element(build_ele, doc)
