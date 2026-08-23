#!/usr/bin/env bash
# Denkzettel: einmalige Einrichtung auf diesem Rechner (Debian- und
# Arch-basierte Systeme, KDE oder GNOME).
#
# Aufruf aus dem Denkzettel-Ordner heraus:
#
#     ./install.sh                     alles: Pakete, whisper.cpp, Modell, Menü
#     ./install.sh --modell medium     anderes Spracherkennungs-Modell
#     ./install.sh --nur-modell        nur das Modell nachladen
#     ./install.sh --ohne-pakete       Systempakete überspringen (schon da)
#     ./install.sh --ohne-tastenkuerzel
#
# Nicht als root ausführen - sudo wird nur für die Systempakete gefragt.
set -euo pipefail

QUELLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIEL="$HOME/.local/share/denkzettel"
APP="$ZIEL/app"
MODELLE="$ZIEL/modelle"
BIN="$HOME/.local/bin"
DESKTOP="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor"
WHISPER_QUELLE="https://github.com/ggml-org/whisper.cpp"
MODELL_QUELLE="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
TASTE="Meta+N"

MODELL_WAHL="turbo"
MIT_PAKETEN=1
MIT_WHISPER=1
MIT_MODELL=1
MIT_APP=1
MIT_TASTE=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --modell) MODELL_WAHL="$2"; shift 2 ;;
        --nur-modell) MIT_PAKETEN=0; MIT_WHISPER=0; MIT_APP=0; MIT_TASTE=0; shift ;;
        --ohne-pakete) MIT_PAKETEN=0; shift ;;
        --ohne-whisper) MIT_WHISPER=0; MIT_MODELL=0; shift ;;
        --ohne-tastenkuerzel) MIT_TASTE=0; shift ;;
        -h|--help) sed -n '2,13p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "Unbekannte Option: $1" >&2; exit 1 ;;
    esac
done

case "$MODELL_WAHL" in
    turbo)  MODELL_DATEI="ggml-large-v3-turbo-q5_0.bin"; MODELL_MB=574 ;;
    medium) MODELL_DATEI="ggml-medium-q5_0.bin";         MODELL_MB=539 ;;
    small)  MODELL_DATEI="ggml-small-q5_1.bin";          MODELL_MB=190 ;;
    base)   MODELL_DATEI="ggml-base-q5_1.bin";           MODELL_MB=60  ;;
    *) echo "Unbekanntes Modell: $MODELL_WAHL (turbo, medium, small, base)" >&2; exit 1 ;;
esac

if [[ $EUID -eq 0 ]]; then
    echo "Bitte NICHT als root ausführen - sudo wird bei Bedarf selbst gefragt." >&2
    exit 1
fi

echo "== Denkzettel einrichten =="
echo

# --------------------------------------------------- Abhängigkeiten
# Jede Zeile: Kennung | Art der Prüfung | Prüfwert | Debian-Paket |
#             Arch-Paket | wofür es gebraucht wird
# Art „befehl“  = muss im PATH liegen
# Art „pymodul“ = muss sich in Python importieren lassen
# Leeres Paketfeld = gehört anderswo dazu, wird nur gemeldet.
ABHAENGIGKEITEN=(
    "Python 3|befehl|python3|python3|python|Grundlage"
    "PyQt6|pymodul|PyQt6.QtWidgets|python3-pyqt6|python-pyqt6|die Fenster"
    "NumPy|pymodul|numpy|python3-numpy|python-numpy|Pegelanzeige"
    "SQLite|pymodul|sqlite3|||Notizspeicher (gehört zu Python)"
    "parecord|befehl|parecord|pulseaudio-utils|libpulse|Tonaufnahme"
    "pactl|befehl|pactl|pulseaudio-utils|libpulse|Mikrofone auflisten"
    "arecord|befehl|arecord|alsa-utils|alsa-utils|Tonaufnahme (Ersatzweg)"
    "git|befehl|git|git|git|whisper.cpp holen"
    "cmake|befehl|cmake|cmake|cmake|whisper.cpp bauen"
    "C++-Compiler|befehl|c++|build-essential|base-devel|whisper.cpp bauen"
    "curl|befehl|curl|curl|curl|Modell herunterladen"
)

if command -v apt-get >/dev/null; then
    PAKETVERWALTER="apt"
elif command -v pacman >/dev/null; then
    PAKETVERWALTER="pacman"
else
    PAKETVERWALTER=""
fi

FEHLEND_TEXT=()
FEHLEND_PAKETE=()

pruefe_abhaengigkeiten() {
    FEHLEND_TEXT=()
    FEHLEND_PAKETE=()
    local eintrag kennung art wert deb arch zweck paket
    for eintrag in "${ABHAENGIGKEITEN[@]}"; do
        IFS='|' read -r kennung art wert deb arch zweck <<<"$eintrag"
        case "$art" in
            befehl)  command -v "$wert" >/dev/null 2>&1 && continue ;;
            pymodul) python3 -c "import $wert" >/dev/null 2>&1 && continue ;;
        esac
        FEHLEND_TEXT+=("$kennung – $zweck")
        [[ "$PAKETVERWALTER" == "apt" ]] && paket="$deb" || paket="$arch"
        [[ -n "$paket" ]] && FEHLEND_PAKETE+=("$paket")
    done
    # Doppelte Paketnamen zusammenfassen (pulseaudio-utils steht zweimal drin)
    if [[ ${#FEHLEND_PAKETE[@]} -gt 0 ]]; then
        mapfile -t FEHLEND_PAKETE < <(printf '%s\n' "${FEHLEND_PAKETE[@]}" | sort -u)
    fi
}

echo "-- Abhängigkeiten prüfen"
pruefe_abhaengigkeiten

if [[ ${#FEHLEND_TEXT[@]} -eq 0 ]]; then
    echo "   Alles vorhanden."
else
    echo "   Es fehlen:"
    printf '     • %s\n' "${FEHLEND_TEXT[@]}"
    if [[ $MIT_PAKETEN -eq 0 ]]; then
        echo
        echo "   --ohne-pakete ist gesetzt, es wird nichts installiert." >&2
        echo "   Ohne diese Pakete läuft Denkzettel nicht." >&2
        exit 1
    fi
    if [[ -z "$PAKETVERWALTER" ]]; then
        echo
        echo "   Weder apt-get noch pacman gefunden - bitte von Hand" >&2
        echo "   installieren, danach: ./install.sh --ohne-pakete" >&2
        exit 1
    fi
    echo
    echo "   Wird nachinstalliert (${PAKETVERWALTER}): ${FEHLEND_PAKETE[*]}"
    if [[ "$PAKETVERWALTER" == "apt" ]]; then
        sudo apt-get update
        sudo apt-get install -y "${FEHLEND_PAKETE[@]}"
    else
        sudo pacman -S --needed --noconfirm "${FEHLEND_PAKETE[@]}"
    fi

    # Nachkontrolle: Ein Paket kann installiert sein und trotzdem fehlt der
    # Befehl (anderer Paketname je Version). Das muss hier auffallen, nicht
    # erst beim ersten Diktat.
    echo
    echo "-- Abhängigkeiten erneut prüfen"
    pruefe_abhaengigkeiten
    if [[ ${#FEHLEND_TEXT[@]} -eq 0 ]]; then
        echo "   Jetzt vollständig."
    else
        echo "   Trotz Installation fehlen weiterhin:" >&2
        printf '     • %s\n' "${FEHLEND_TEXT[@]}" >&2
        echo >&2
        echo "   Bitte diese Pakete von Hand suchen - unter dieser" >&2
        echo "   Distribution heißen sie offenbar anders. Danach:" >&2
        echo "     ./install.sh --ohne-pakete" >&2
        exit 1
    fi
fi
echo

mkdir -p "$ZIEL" "$MODELLE" "$BIN" "$DESKTOP" "$HOME/.log"

# ----------------------------------------------------------- whisper.cpp
if [[ $MIT_WHISPER -eq 1 ]]; then
    echo "-- Spracherkennung whisper.cpp"
    if [[ -x "$ZIEL/whisper.cpp/build/bin/whisper-cli" ]]; then
        echo "   schon gebaut: $ZIEL/whisper.cpp/build/bin/whisper-cli"
    else
        if [[ -d "$ZIEL/whisper.cpp/.git" ]]; then
            git -C "$ZIEL/whisper.cpp" pull --ff-only
        else
            git clone --depth 1 "$WHISPER_QUELLE" "$ZIEL/whisper.cpp"
        fi
        echo "   wird übersetzt - das dauert ein paar Minuten"
        cmake -S "$ZIEL/whisper.cpp" -B "$ZIEL/whisper.cpp/build" \
              -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_EXAMPLES=ON
        # Erst nur das Programm bauen, das gebraucht wird. Heißt das Ziel in
        # dieser whisper.cpp-Fassung anders, wird alles gebaut - dauert
        # länger, scheitert aber nicht am Namen eines Bauziels.
        if ! cmake --build "$ZIEL/whisper.cpp/build" --config Release \
                   -j "$(nproc)" --target whisper-cli; then
            echo "   Bauziel whisper-cli gibt es nicht - baue alles"
            cmake --build "$ZIEL/whisper.cpp/build" --config Release -j "$(nproc)"
        fi
    fi
    if [[ ! -x "$ZIEL/whisper.cpp/build/bin/whisper-cli" ]]; then
        echo "   whisper-cli wurde nicht gebaut - Abbruch." >&2
        exit 1
    fi
    echo
fi

# --------------------------------------------------------------- Modell
if [[ $MIT_MODELL -eq 1 ]]; then
    echo "-- Spracherkennungs-Modell ($MODELL_WAHL, etwa ${MODELL_MB} MB)"
    if [[ -s "$MODELLE/$MODELL_DATEI" ]]; then
        echo "   schon da: $MODELLE/$MODELL_DATEI"
    else
        curl -L --fail --progress-bar -o "$MODELLE/$MODELL_DATEI.teil" \
             "$MODELL_QUELLE/$MODELL_DATEI"
        # Erst umbenennen, wenn der Download vollständig ist - sonst hält
        # ein abgebrochener Download das Programm für einsatzbereit.
        mv "$MODELLE/$MODELL_DATEI.teil" "$MODELLE/$MODELL_DATEI"
    fi
    echo
fi

# ------------------------------------------------------------ Programm
if [[ $MIT_APP -eq 1 ]]; then
    echo "-- Programmdateien nach $APP"
    rm -rf "$APP"
    mkdir -p "$APP"
    cp -r "$QUELLE/denkzettel" "$APP/"
    cp -r "$QUELLE/assets" "$APP/"
    find "$APP" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

    cat > "$BIN/denkzettel" <<LAUNCHER
#!/usr/bin/env bash
# Startet Denkzettel aus $APP
export PYTHONPATH="$APP\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m denkzettel "\$@"
LAUNCHER
    chmod +x "$BIN/denkzettel"

    echo "-- Symbole"
    for GROESSE in 512 256 128 64 48 32; do
        if [[ -f "$QUELLE/assets/icon-$GROESSE.png" ]]; then
            mkdir -p "$ICONS/${GROESSE}x${GROESSE}/apps"
            cp "$QUELLE/assets/icon-$GROESSE.png" \
               "$ICONS/${GROESSE}x${GROESSE}/apps/denkzettel.png"
        fi
    done
    command -v gtk-update-icon-cache >/dev/null && \
        gtk-update-icon-cache -f -t "$ICONS" >/dev/null 2>&1 || true

    echo "-- Startmenü-Einträge"
    cp "$QUELLE/desktop/denkzettel.desktop" "$DESKTOP/"
    sed "s|@TASTE@|$TASTE|" "$QUELLE/desktop/denkzettel-erfassen.desktop" \
        > "$DESKTOP/denkzettel-erfassen.desktop"
    command -v update-desktop-database >/dev/null && \
        update-desktop-database "$DESKTOP" >/dev/null 2>&1 || true
    command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

    # Gefundenes whisper.cpp fest eintragen: spart beim Start die Suche und
    # verhindert, dass ein gleichnamiges anderes Programm genommen wird.
    if [[ -x "$ZIEL/whisper.cpp/build/bin/whisper-cli" ]]; then
        PYTHONPATH="$APP" python3 - <<'PYEND'
from denkzettel import config
cfg = config.laden()
cfg.set("erkennung", "programm",
        str(config.DATA_DIR / "whisper.cpp" / "build" / "bin" / "whisper-cli"))
config.speichern(cfg)
PYEND
    fi
    echo
fi

# ------------------------------------------------------------- Mikrofon
# Die Mikrofon-Auswahl steht bewusst NICHT hier, sondern in der Einführung
# beim ersten Programmstart (Stephan, 2026-08-23). Eine Frage, die einmal
# im Terminal durchläuft, sieht man nie wieder - und man beantwortet sie,
# bevor man das Programm überhaupt kennt. Im Fenster kann man die Wahl
# außerdem gleich mit dem Pegelbalken ausprobieren.
if [[ $MIT_APP -eq 1 ]]; then
    echo "-- Mikrofone auf diesem Rechner"
    PYTHONPATH="$APP" python3 -m denkzettel mikrofone || true
    echo "   Ausgewählt wird beim ersten Start von Denkzettel."
    echo
fi

# --------------------------------------------------------- Tastenkürzel
if [[ $MIT_TASTE -eq 1 ]]; then
    echo "-- Tastenkürzel $TASTE für „sofort aufnehmen“"
    SCHREIBTISCH="${XDG_CURRENT_DESKTOP:-}"
    if [[ "$SCHREIBTISCH" == *GNOME* ]] && command -v gsettings >/dev/null; then
        PFAD="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/denkzettel/"
        LISTE="$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)"
        if [[ "$LISTE" != *"$PFAD"* ]]; then
            if [[ "$LISTE" == "@as []" ]]; then
                NEU="['$PFAD']"
            else
                NEU="${LISTE%]}, '$PFAD']"
            fi
            gsettings set org.gnome.settings-daemon.plugins.media-keys \
                custom-keybindings "$NEU"
        fi
        SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$PFAD"
        gsettings set "$SCHEMA" name "Denkzettel: Gedanken aufnehmen"
        gsettings set "$SCHEMA" command "$BIN/denkzettel erfassen"
        gsettings set "$SCHEMA" binding "<Super>n"
        echo "   in GNOME eingetragen: Super+N"
    elif [[ "$SCHREIBTISCH" == *KDE* ]]; then
        echo "   In KDE steht das Kürzel in der Menü-Datei (X-KDE-Shortcuts)."
        echo "   Falls es nicht sofort greift: Systemeinstellungen ->"
        echo "   Kurzbefehle -> Denkzettel, oder einmal ab- und anmelden."
    else
        echo "   Schreibtisch „${SCHREIBTISCH:-unbekannt}“ - bitte von Hand"
        echo "   ein Kürzel auf diesen Befehl legen:"
        echo "     $BIN/denkzettel erfassen"
    fi
    echo
fi

# ------------------------------------------------------------- Abschluss
if [[ ":$PATH:" != *":$BIN:"* ]]; then
    echo "!! $BIN liegt nicht im PATH."
    echo "   Diese Zeile in ~/.bashrc bzw. ~/.zshrc ergänzen:"
    echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
fi

echo "== Fertig =="
echo
PYTHONPATH="$APP" python3 -m denkzettel pruefen || true
echo
echo "Notizbuch öffnen:        denkzettel"
echo "Sofort etwas diktieren:  denkzettel erfassen   (oder $TASTE)"
