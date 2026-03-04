"""
rohr.py – Rohr-Geometrie-Modul für KanalbauHaltung

Erstellt ein hohles zylindrisches Rohr entlang eines beliebigen Vektors
(Rohrachse) zwischen zwei 3D-Punkten (Rohrsohle Start → Rohrsohle Ende).

Die Zylinderachse wird direkt aus dem Differenzvektor abgeleitet, sodass
das Gefälle automatisch abgebildet wird.

AxisPlacement3D-Konventionen (Allplan 2024):
  Für orientierte Zylinder (beliebige Achsrichtung) muss die Signatur
    AxisPlacement3D(Point3D, xvector, zvector)
  verwendet werden, wobei zvector die Zylinderachse definiert und xvector
  senkrecht dazu stehen muss.
  NICHT gültig: AxisPlacement3D(Point3D, Vector3D)  ← ArgumentError
"""

import math

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BasisElements as AllplanBasisElements


def _perp_vector(nx: float, ny: float, nz: float) -> AllplanGeo.Vector3D:
    """
    Berechnet einen Einheitsvektor senkrecht zu (nx, ny, nz).
    Wird als X-Achse für AxisPlacement3D(Point3D, xvector, zvector) benötigt.
    """
    # Kreuzprodukt mit (0, 0, 1) – funktioniert für fast alle Richtungen
    if abs(nz) < 0.9:
        # (nx,ny,nz) × (0,0,1) = (ny·1 − nz·0,  nz·0 − nx·1,  nx·0 − ny·0)
        #                       = (ny, -nx, 0)
        px, py, pz = ny, -nx, 0.0
    else:
        # Fast parallel zu Z → Kreuzprodukt mit (1, 0, 0) statt
        # (nx,ny,nz) × (1,0,0) = (ny·0 − nz·0,  nz·1 − nx·0,  nx·0 − ny·1)
        #                       = (0, nz, -ny)
        px, py, pz = 0.0, nz, -ny

    length = math.sqrt(px * px + py * py + pz * pz)
    if length < 1e-9:
        return AllplanGeo.Vector3D(1.0, 0.0, 0.0)
    return AllplanGeo.Vector3D(px / length, py / length, pz / length)


def create_rohr(
        start_pt: AllplanGeo.Point3D,
        end_pt:   AllplanGeo.Point3D,
        r_aussen: float,
        r_innen:  float,
        common_props) -> list:
    """
    Erstellt ein hohles Rohr von start_pt nach end_pt.

    Parameter
    ---------
    start_pt     : 3D-Punkt der Rohrsohle am Startschacht (Ursprung)
    end_pt       : 3D-Punkt der Rohrsohle am Endschacht
    r_aussen     : Außenradius des Rohres (mm)
    r_innen      : Innenradius des Rohres (mm)
    common_props : AllplanBaseElements.CommonProperties

    Rückgabe
    --------
    Liste [ModelElement3D] – ein hohles BRep3D-Rohr

    Hinweise
    --------
    - BRep3D.CreateCylinder verlängert den Zylinder entlang der lokalen Z-Achse
      der AxisPlacement3D (= zvector des Placements).
    - height = euklidische Distanz start_pt → end_pt (Schrägmaß).
    - AxisPlacement3D(Point3D, xvector, zvector): zvector = Rohrrichtung (normiert),
      xvector = beliebiger Vektor senkrecht zur Rohrrichtung.
    """
    r_innen = max(r_innen, 10.0)

    # Richtungsvektor und Länge
    dx = end_pt.X - start_pt.X
    dy = end_pt.Y - start_pt.Y
    dz = end_pt.Z - start_pt.Z
    laenge = math.sqrt(dx * dx + dy * dy + dz * dz)

    if laenge < 1.0:
        # Entartetes Rohr – nichts erzeugen
        return []

    # Normierter Richtungsvektor (= lokale Z-Achse des Zylinders)
    nx, ny, nz = dx / laenge, dy / laenge, dz / laenge

    z_vec = AllplanGeo.Vector3D(nx, ny, nz)
    x_vec = _perp_vector(nx, ny, nz)

    # AxisPlacement3D(Point3D, xvector, zvector) – einzige gültige 2-Vektor-Signatur
    axis = AllplanGeo.AxisPlacement3D(start_pt, x_vec, z_vec)

    outer = AllplanGeo.BRep3D.CreateCylinder(axis, r_aussen, laenge, True, True)
    inner = AllplanGeo.BRep3D.CreateCylinder(axis, r_innen,  laenge, True, True)

    err, hollow = AllplanGeo.MakeSubtraction(outer, inner)
    geo = hollow if (not err and not hollow.IsEmpty()) else outer

    return [AllplanBasisElements.ModelElement3D(common_props, geo)]


def rohr_end_point(start_pt: AllplanGeo.Point3D,
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
    haltungslaenge: Horizontale Rohrlänge (mm) — Schlauchlänge entlang der Trasse
    gefalle_pct   : Gefälle in Prozent (positiv = Rohr fällt in X-Richtung ab)

    Rückgabe
    --------
    AllplanGeo.Point3D – Endpunkt der Rohrsohle
    """
    alpha = math.atan(gefalle_pct / 100.0)
    dx = haltungslaenge * math.cos(alpha)
    dz = -haltungslaenge * math.sin(alpha)   # negativ = abfallend

    return AllplanGeo.Point3D(
        start_pt.X + dx,
        start_pt.Y,
        start_pt.Z + dz
    )
