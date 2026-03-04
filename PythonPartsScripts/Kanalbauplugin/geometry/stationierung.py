"""
stationierung.py – Stationierungs-Annotationen für KanalbauHaltung

Erzeugt Text-Elemente entlang der Rohrachse im definierten Abstand.

Stationierungsformat: km+m  (z.B. "0+000", "0+020", "0+040")
Der Text wird leicht oberhalb der Rohrsohle und senkrecht zur Rohrachse
versetzt platziert.

Koordinatensystem des Aufrufers:
  start_pt = Rohrsohle Startschacht (Ursprung)
  end_pt   = Rohrsohle Endschacht
"""

import math

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BasisElements as AllplanBasisElements


def _format_station(meter: float, start_offset_m: float = 0.0) -> str:
    """
    Formatiert einen Stationswert als "km+m"-String.
    Beispiel: 1234.5 → "1+234"
    """
    total_m = int(round(meter + start_offset_m))
    km  = total_m // 1000
    rest = total_m  % 1000
    return f"{km}+{rest:03d}"


def create_stationierung(
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
    text_offset    : Versatz des Textes senkrecht zur Achse und nach oben (mm)
    start_offset_m : Startstation in Metern (für Nummerierung)
    common_props   : AllplanBaseElements.CommonProperties

    Rückgabe
    --------
    Liste von AllplanBasisElements.ModelElement3D (TextElement)
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
    # Zusätzlich vertikal (+Z) für Abstand oberhalb der Sohle
    qx = -uy
    qy =  ux
    qz =  0.0

    # Anzahl Stationierungsmarken (Start = 0, dann jeden abstand mm)
    anzahl = int(laenge / abstand)

    # Textausrichtungswinkel (Drehung im Grundriss, Grad)
    # Winkel der Rohrachse in der XY-Ebene
    winkel_grad = math.degrees(math.atan2(dy, dx))

    for i in range(anzahl + 1):
        s = i * abstand                 # Bogenlänge entlang der Achse (mm)
        if s > laenge + 0.1:
            break

        # Punkt auf der Rohrachse
        pt_achse = AllplanGeo.Point3D(
            start_pt.X + ux * s,
            start_pt.Y + uy * s,
            start_pt.Z + uz * s
        )

        # Textposition: Rohrachsenpunkt + Querversatz (Point2D – TextElement ist 2D)
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
