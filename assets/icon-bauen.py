#!/usr/bin/env python3
"""
Erzeugt das Denkzettel-Icon aus dem DialOS-App-Icon.

Denkzettel gehört zur DialOS-Familie und soll auch so aussehen: derselbe
Kreis, dieselbe Dame, dieselbe tragende Hand, derselbe Blau-Grün-Verlauf.
Unterschied ist die rechte Hälfte - statt der Schallwellen kommt eine
geschriebene Zeile aus dem Mund, und ein Stift schreibt sie. Das ist
Absicht: Wenn beide Programme nebeneinander in der Fensterleiste liegen,
muss man sie bei 32 Pixeln auseinanderhalten können.

Die Vorlage wird nicht übermalt, sondern in eine Strichzeichnung mit
Transparenz zurückgerechnet (Weiß = durchsichtig, Farbe = Linie). Nur so
lassen sich die Schallwellen sauber entfernen und dieselbe Zeichnung
sowohl auf hellem als auch auf dunklem Grund verwenden.

Aufruf (die DialOS-Vorlage muss daneben liegen):

    python3 assets/icon-bauen.py [--vorlage PFAD]
"""
import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent
VORLAGE_STANDARD = ASSETS.parent.parent / "DialOS" / "assets" / "app-icon-light.png"

S = 4            # Supersampling gegen Treppenkanten
N = 512 * S      # Arbeitsgröße

CYAN = (0, 173, 212)      # aus dem DialOS-Icon abgetastet
GRUEN = (98, 197, 0)
NAVY = (13, 27, 51)       # Hintergrund der dunklen DialOS-Variante
WEISS = (255, 255, 255)

# Stephans Entscheidung (2026-08-24): die dunkle Kreisscheibe auf hellem
# Hintergrund, die helle auf dunklem - umgekehrt zur naheliegenden
# Zuordnung. „app-icon-light.png“ heißt weiterhin „Datei für helle
# Umgebungen“, ihr Bildinhalt ist aber die dunkle Scheibe. Das Startmenü
# bekommt dieselbe Wahl: „menue-*.png“ übernimmt die Farbe von
# GRUND_HELL, weil Stephans Panel hell ist.
GRUND_HELL = NAVY
GRUND_DUNKEL = WEISS

# Bereich der drei Schallwellen in der Vorlage (512er-Koordinaten)
WELLEN = (306, 175, 425, 358)

# Der Ring der Vorlage liegt je nach Richtung bei Radius 215-236 (Mitte
# 255,5). Alles Neue bleibt innerhalb von MAX_RADIUS - der Stift darf den
# Bogen nicht berühren, auch nicht bei 32 Pixeln, wo ein Pixel gut 8
# Einheiten dieser 512er-Koordinaten entspricht.
MITTE = 255.5
MAX_RADIUS = 192

GROESSEN = (512, 256, 128, 64, 48, 32)


def strichzeichnung(vorlage: Path) -> tuple[Image.Image, Image.Image]:
    """Vorlage in (Linien-RGBA, Kreisscheibe-Maske) zerlegen."""
    im = Image.open(vorlage).convert("RGBA").resize((N, N), Image.LANCZOS)
    scheibe = im.getchannel("A")
    rgb = im.convert("RGB").load()
    scheibe_px = scheibe.load()

    linien = Image.new("RGBA", (N, N))
    lp = linien.load()
    for y in range(N):
        for x in range(N):
            if scheibe_px[x, y] < 8:
                continue
            r, g, b = rgb[x, y]
            a = 255 - min(r, g, b)          # Deckkraft = Abstand zu Weiß
            if a < 8:
                continue
            f = 255 / a                      # Farbe auf volle Sättigung zurück
            lp[x, y] = (
                max(0, min(255, int(255 - (255 - r) * f))),
                max(0, min(255, int(255 - (255 - g) * f))),
                max(0, min(255, int(255 - (255 - b) * f))),
                min(a, scheibe_px[x, y]),
            )
    return linien, scheibe


def verlauf_maske(maske: Image.Image, c1, c2) -> Image.Image:
    """Graustufen-Maske mit waagrechtem Farbverlauf einfärben."""
    g = Image.new("RGB", (N, N))
    d = ImageDraw.Draw(g)
    for i in range(N):
        t = i / (N - 1)
        d.line([(i, 0), (i, N)],
               fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    g = g.convert("RGBA")
    g.putalpha(maske)
    return g


def stift(d: ImageDraw.ImageDraw, spitze, winkel_grad, laenge, breite):
    """Bleistift: Spitze, Korpus, abgerundetes Ende."""
    a = math.radians(winkel_grad)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    tx, ty = spitze
    h = breite / 2
    p = lambda t, s: (tx + dx * t + nx * s, ty + dy * t + ny * s)  # noqa: E731

    spitzen_l = breite * 1.15
    d.polygon([p(0, 0), p(spitzen_l, h), p(spitzen_l, -h)], fill=255)
    d.polygon([p(spitzen_l, h), p(laenge, h), p(laenge, -h), p(spitzen_l, -h)], fill=255)
    d.ellipse([tx + dx * laenge - h, ty + dy * laenge - h,
               tx + dx * laenge + h, ty + dy * laenge + h], fill=255)


def stift_kerbe(d: ImageDraw.ImageDraw, spitze, winkel_grad, breite, strich):
    """Trennlinie zwischen Spitze und Korpus - wird ausgestanzt."""
    a = math.radians(winkel_grad)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    tx, ty = spitze
    h, t = breite / 2, breite * 1.15
    d.line([(tx + dx * t + nx * h, ty + dy * t + ny * h),
            (tx + dx * t - nx * h, ty + dy * t - ny * h)], fill=255, width=int(strich))


def schreiblinie(d: ImageDraw.ImageDraw, x0, x1, y, amp, perioden, strich):
    """Handschrift-Schnörkel, der zum Stift hin größer wird."""
    pts = []
    for i in range(241):
        t = i / 240
        pts.append((x0 + (x1 - x0) * t,
                    y + math.sin(t * math.pi * 2 * perioden) * amp * (0.35 + 0.65 * t)))
    d.line(pts, fill=255, width=int(strich), joint="curve")


def groesster_radius(maske: Image.Image) -> float:
    """Wie weit reicht das Neugezeichnete vom Mittelpunkt weg (512er-Maß)?"""
    kasten = maske.getbbox()
    if kasten is None:
        return 0.0
    px = maske.load()
    weit = 0.0
    for y in range(kasten[1], kasten[3]):
        for x in range(kasten[0], kasten[2]):
            if px[x, y] < 64:
                continue
            r = math.hypot(x / S - MITTE, y / S - MITTE)
            if r > weit:
                weit = r
    return weit


def zeichnung(vorlage: Path) -> tuple[Image.Image, Image.Image]:
    linien, scheibe = strichzeichnung(vorlage)

    # Schallwellen entfernen - Denkzettel spricht nicht, es schreibt mit.
    x0, y0, x1, y1 = [int(v * S) for v in WELLEN]
    linien.paste((0, 0, 0, 0), (x0, y0, x1, y1))

    spitze = (376 * S, 301 * S)
    winkel, laenge, breite = -63, 98 * S, 24 * S

    maske = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(maske)
    schreiblinie(d, 314 * S, 372 * S, 301 * S, 13 * S, 1.75, 11 * S)
    stift(d, spitze, winkel, laenge, breite)

    weit = groesster_radius(maske)
    if weit > MAX_RADIUS:
        raise SystemExit(f"Stift/Schreiblinie reichen bis Radius {weit:.1f} und "
                         f"berühren damit den Bogen (erlaubt: {MAX_RADIUS}).")
    print(f"Abstand geprüft: äußerster Punkt bei Radius {weit:.1f} "
          f"(Ring-Innenkante ab 215) - Luft: {215 - weit:.1f}")

    kerbe = Image.new("L", (N, N), 0)
    stift_kerbe(ImageDraw.Draw(kerbe), spitze, winkel, breite, 5 * S)

    neu = verlauf_maske(maske, CYAN, GRUEN)
    neu.paste((0, 0, 0, 0), (0, 0), kerbe)
    linien.alpha_composite(neu)
    return linien, scheibe


def speichern(linien, scheibe, grund, ziel: Path, groesse: int):
    """Linien auf eine Kreisscheibe in der gewünschten Grundfarbe setzen."""
    if grund is None:                        # durchsichtig
        bild = linien.copy()
    else:
        bild = Image.new("RGBA", (N, N), grund + (0,))
        bild.putalpha(scheibe)
        bild.alpha_composite(linien)
    bild.resize((groesse, groesse), Image.LANCZOS).save(ziel)


def main():
    ap = argparse.ArgumentParser(description="Denkzettel-Icon erzeugen")
    ap.add_argument("--vorlage", type=Path, default=VORLAGE_STANDARD)
    args = ap.parse_args()

    if not args.vorlage.exists():
        raise SystemExit(f"DialOS-Vorlage nicht gefunden: {args.vorlage}\n"
                         f"Mit --vorlage den Pfad zu app-icon-light.png angeben.")

    linien, scheibe = zeichnung(args.vorlage)

    speichern(linien, scheibe, GRUND_HELL, ASSETS / "app-icon-light.png", 512)
    speichern(linien, scheibe, GRUND_DUNKEL, ASSETS / "app-icon-dark.png", 512)
    for g in GROESSEN:
        speichern(linien, scheibe, None, ASSETS / f"icon-{g}.png", g)
        # Fürs Startmenü: dieselbe Farbe wie app-icon-light.png, in jeder
        # Icon-Theme-Größe. Ein Menü zeigt immer nur eine Fassung, kein
        # automatisches Umschalten nach Systemthema - Stephans Panel ist
        # hell, deshalb die dunkle Scheibe.
        speichern(linien, scheibe, GRUND_HELL, ASSETS / f"menue-{g}.png", g)
    print(f"Icons geschrieben nach {ASSETS}")


if __name__ == "__main__":
    main()
