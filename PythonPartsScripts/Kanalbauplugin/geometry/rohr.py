"""
rohr.py – Rohr-Geometrie-Modul für KanalbauHaltung

Erstellt ein hohles zylindrisches Rohr entlang eines beliebigen Vektors
(Rohrachse) zwischen zwei 3D-Punkten (Rohrsohle Start → Rohrsohle Ende).

Die Zylinderachse wird direkt aus dem Differenzvektor abgeleitet, sodass
das Gefälle automatisch abgebildet wird.
"""

import math

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BasisElements as AllplanBasisElements


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
    - Zylinderachse = Vektor(start_pt → end_pt), normalisiert auf Länge 1
    - BRep3D.CreateCylinder erwartet height = Länge entlang der lokalen Z-Achse
      der AxisPlacement3D. Wir übergeben den Richtungsvektor als lokale Z-Achse
      und height = euklidische Distanz zwischen den Punkten.
    - Beim Zusammensetzen mit den Schächten liegt der Rohrmittelpunkt auf
      der Schachtachse; die Rohrsohle (unterster Punkt des Querschnitts) liegt
      r_aussen unterhalb des Mittelpunkts. Für die vereinfachte Darstellung
      wird hier der übergebene start_pt als Achsenmittelpunkt interpretiert.
    """
    r_innen = max(r_innen, 10.0)

    # Richtungsvektor
    dx = end_pt.X - start_pt.X
    dy = end_pt.Y - start_pt.Y
    dz = end_pt.Z - start_pt.Z
    laenge = math.sqrt(dx * dx + dy * dy + dz * dz)

    if laenge < 1.0:
        # Entartetes Rohr – nichts erzeugen
        return []

    richtung = AllplanGeo.Vector3D(dx, dy, dz)

    # AxisPlacement3D: Ursprung = start_pt, lokale Z-Achse = Rohrrichtung
    axis = AllplanGeo.AxisPlacement3D(start_pt, richtung)

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
