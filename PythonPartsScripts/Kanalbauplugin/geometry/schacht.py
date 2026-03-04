"""
schacht.py – Schacht-Geometrie-Modul für KanalbauHaltung

Erstellt einen vollständigen Kanalschacht (Startschacht oder Endschacht) als
Liste von ModelElement3D-Objekten. Jedes Bauteil (Sohlplatte, Schachtring,
Konus, Aufbau) wird separat zurückgegeben, damit es in Allplan einzeln
selektiert werden kann.

Koordinatenursprung des Aufrufers:
  origin = Punkt an der Rohrsohle (Invert) des einmündenden Rohres
  Z wächst vertikal nach oben

Geometrischer Aufbau (von unten nach oben):
  1. Sohlplatte   – Cuboid, zentriert, Dicke nach unten (-Z)
  2. Schachtring  – Hohlzylinder (BRep3D Subtraktion)
  3. Konus        – Kegelstumpf (optional, BRep3D Subtraktion + Clipping)
  4. Aufbau/Hals  – Kleiner Hohlzylinder

AxisPlacement3D-Konventionen (Allplan 2024):
  Gültige Signaturen:
    AxisPlacement3D()                              – Standard Z-oben
    AxisPlacement3D(Point3D)                       – Z-oben, Ursprung = point
    AxisPlacement3D(Point3D, xvector, zvector)     – vollständig orientiert
  NICHT gültig: AxisPlacement3D(Point3D, Vector3D)  ← würde ArgumentError werfen
"""

import math

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BasisElements as AllplanBasisElements


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _hollow_cylinder(origin: AllplanGeo.Point3D,
                     r_aussen: float,
                     r_innen: float,
                     hoehe: float,
                     common_props) -> AllplanBasisElements.ModelElement3D | None:
    """
    Erstellt einen Hohlzylinder (BRep3D) mit senkrechter Achse (+Z).
    Gibt ModelElement3D zurück oder None bei Fehler.
    """
    r_innen = max(r_innen, 10.0)
    # AxisPlacement3D(Point3D) → Standard-Orientierung: lokale Z-Achse = Welt-Z (+oben)
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
      1. Vollständigen Kegel (Spitze liegt über dem Stumpf) erzeugen.
      2. Mit Clipping-Quader über z=origin.Z+hoehe abschneiden.
      3. Innenform (kleinerer Kegelstumpf) erzeugen und subtrahieren.

    Gibt ModelElement3D zurück oder None bei Fehler.
    """
    r_innen_unten = max(r_unten - wandstaerke, 10.0)
    r_innen_oben  = max(r_oben  - wandstaerke, 10.0)

    def _make_frustum_brep(r_bottom: float, r_top: float) -> AllplanGeo.BRep3D | None:
        """Hilfsfunktion: Vollkegel + Clipping → Kegelstumpf als BRep3D."""
        if abs(r_bottom - r_top) < 0.1:
            # Degeneriert: Zylinder statt Kegel
            # AxisPlacement3D(Point3D) → Standard Z-oben
            axis = AllplanGeo.AxisPlacement3D(origin)
            return AllplanGeo.BRep3D.CreateCylinder(axis, r_bottom, hoehe, True, True)

        # Spitzenhöhe über dem Ursprung (ähnliche Dreiecke)
        apex_h = hoehe * r_bottom / (r_bottom - r_top)
        apex_pt = AllplanGeo.Point3D(
            origin.X,
            origin.Y,
            origin.Z + apex_h
        )

        cone3d = AllplanGeo.Cone3D(
            AllplanGeo.AxisPlacement3D(origin),   # Standard Z-oben
            r_bottom,
            0.0,
            apex_pt
        )
        full_cone = AllplanGeo.BRep3D.CreateCone(cone3d, True)

        # Clipping-Quader oberhalb z_trunkierung
        # AxisPlacement3D(Point3D) → Standard Z-oben; Höhe des Quaders wächst in +Z
        z_cut = origin.Z + hoehe
        clip_origin = AllplanGeo.Point3D(origin.X - 20000, origin.Y - 20000, z_cut)
        clip = AllplanGeo.BRep3D.CreateCuboid(
            AllplanGeo.AxisPlacement3D(clip_origin),   # Standard Z-oben
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


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def create_schacht(
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

    Parameter
    ---------
    origin        : Punkt an der Rohrsohle des Zuflussrohres (X, Y, Z)
    schacht_dm    : Aussendurchmesser des Schachtrings (mm)
    wandstaerke   : Wandstärke Schachtring (mm)
    tiefe         : Nutztiefe des Schachts (Oberkante Sohlplatte bis Oberkante Ring) (mm)
    mit_konus     : True = Konus vorhanden
    konus_hoehe   : Höhe des Konus (mm)
    konus_dn_oben : Aussendurchmesser des Konus am oberen Ende (mm)
    aufbau_hoehe  : Höhe des Halsrings / Aufbaus (mm)
    aufbau_dn     : Aussendurchmesser des Aufbaus (mm)
    sohlplatte_h  : Stärke der Sohlplatte (mm), ragt nach unten aus origin
    common_props  : AllplanBaseElements.CommonProperties

    Rückgabe
    --------
    Liste [ModelElement3D, ...] – enthält Sohlplatte, Schachtring, ggf. Konus, ggf. Aufbau
    """
    elements: list = []

    r_aussen = schacht_dm / 2.0
    r_innen  = max(r_aussen - wandstaerke, 10.0)

    # Z-Ebenen (aufsteigend)
    z0 = origin.Z - sohlplatte_h          # Unterkante Sohlplatte
    z1 = origin.Z                          # Oberkante Sohlplatte = Unterkante Schachtring
    z2 = z1 + tiefe                        # Oberkante Schachtring
    z3 = z2 + (konus_hoehe if mit_konus else 0.0)  # Oberkante Konus
    # z4 = z3 + aufbau_hoehe              # Oberkante Aufbau (nur Referenz)

    # ------------------------------------------------------------------
    # 1. SOHLPLATTE (Cuboid, zentriert, ragt nach unten)
    # AxisPlacement3D(Point3D) → Standard Z-oben; Höhe wächst in +Z
    # ------------------------------------------------------------------
    sohlplatte_origin = AllplanGeo.Point3D(
        origin.X - r_aussen,
        origin.Y - r_aussen,
        z0
    )
    sohlplatte_geo = AllplanGeo.BRep3D.CreateCuboid(
        AllplanGeo.AxisPlacement3D(sohlplatte_origin),
        schacht_dm,    # Länge in X
        schacht_dm,    # Breite in Y
        sohlplatte_h   # Höhe in Z
    )
    elements.append(AllplanBasisElements.ModelElement3D(common_props, sohlplatte_geo))

    # ------------------------------------------------------------------
    # 2. SCHACHTRING (Hohlzylinder)
    # ------------------------------------------------------------------
    ring_origin = AllplanGeo.Point3D(origin.X, origin.Y, z1)
    ring_ele = _hollow_cylinder(ring_origin, r_aussen, r_innen, tiefe, common_props)
    if ring_ele is not None:
        elements.append(ring_ele)

    # ------------------------------------------------------------------
    # 3. KONUS (optional, Kegelstumpf)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 4. AUFBAU / HALSRING (Hohlzylinder, kleiner Durchmesser)
    # ------------------------------------------------------------------
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


def deckel_position(origin: AllplanGeo.Point3D,
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
