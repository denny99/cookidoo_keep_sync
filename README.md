# Cookidoo → Google Keep Sync

Eine Home-Assistant Custom Integration, die deine **Cookidoo-Einkaufsliste** in eine **Google-Keep-Liste** synchronisiert und die Items dabei nach deiner persönlichen **Supermarkt-Reihenfolge** sortiert. Unbekannte Artikel werden über deinen konfigurierten **Conversation-Agent** (z.B. Claude) in einem einzigen Bulk-Call klassifiziert und für die Zukunft gelernt.

## Warum?

Cookidoo schreibt beim Übernehmen eines Rezepts brav alle Zutaten in seine Einkaufsliste — aber:

- die Cookidoo-Liste ist **read-only und nicht sortierbar**
- die Reihenfolge ist die Reihenfolge, in der das Rezept Zutaten erwähnt — nicht die Reihenfolge, in der sie im Markt liegen

Diese Integration löst beides: sie kopiert die Items in eine vollwertige Google-Keep-Liste und sortiert sie so, wie du im Laden läufst.

## Features

- **Cookidoo → Keep merge & sort**: alle offenen Items aus Cookidoo + alle Items, die du selbst manuell in Keep aufgeschrieben hast, werden zusammengeführt und gemeinsam sortiert
- **Keine Doppel-Imports**: nach dem Kopieren wird das Cookidoo-Item dort als erledigt markiert, sodass es beim nächsten Sync nicht erneut auftaucht (sofern die Cookidoo-Integration `update_item` unterstützt)
- **Bereits abgehakte Items werden ignoriert** (in beiden Listen)
- **Sortierung nach individueller Markt-Reihenfolge** (z.B. Obst/Gemüse → Wurst → Käse → Getränke)
- **Keyword-basierte Klassifikation** (offline, kostenlos, ~90% Trefferquote)
- **Bulk-LLM-Fallback** für unbekannte Items: ein einziger Call an Claude/OpenAI/Ollama klassifiziert alle Restartikel auf einmal — strukturiertes `[N] Kategorie`-Format wird per Regex geparst
- **Auto-lernen**: jedes vom LLM klassifizierte Item wird gespeichert und beim nächsten Sync per Keyword-Match aufgelöst — der LLM wird nur für wirklich neue Items befragt
- **Native HA Todo-Entity für die Kategorien-Reihenfolge**: die Integration legt automatisch eine Liste `todo.cookidoo_keep_kategorien` an, deren **Reihenfolge per Drag & Drop in der HA-UI änderbar** ist
- Optional: Override-Todo-Liste, falls du die Kategorien woanders pflegen willst (z.B. eine Keep-Liste, die du mit deinem Partner teilst)
- Service `cookidoo_keep_sync.sync` für Buttons, Automationen oder Sprachbefehle

## Voraussetzungen

- Home Assistant ≥ 2024.6 (wegen Todo-Platform mit Reorder)
- Eine **Cookidoo-Integration**, die eine `todo`-Entity exposed (z.B. [miaucl/ha-cookidoo](https://github.com/miaucl/ha-cookidoo))
- Eine **Google-Keep-Integration**, die eine `todo`-Entity exposed (z.B. [watkins-matt/home-assistant-google-keep-sync](https://github.com/watkins-matt/home-assistant-google-keep-sync))
- *(Optional, empfohlen)* eine **Conversation-Integration**, z.B. die offizielle Anthropic-Integration (Claude), OpenAI Conversation, Ollama oder Google Generative AI

## Installation

### Via HACS (empfohlen)

1. HACS → **Integrationen** → Drei-Punkte-Menü → **Benutzerdefinierte Repositories**
2. Repository: `https://github.com/denny99/cookidoo_keep_sync`
3. Kategorie: `Integration`
4. Hinzufügen → in der HACS-Liste **Cookidoo → Google Keep Sync** suchen → installieren
5. Home Assistant neu starten

### Manuell

```bash
cd /config/custom_components
git clone https://github.com/denny99/cookidoo_keep_sync.git tmp
mv tmp/custom_components/cookidoo_keep_sync .
rm -rf tmp
```

Danach Home Assistant neu starten.

## Setup

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → "Cookidoo → Google Keep Sync"**
2. Felder ausfüllen:
   - **Cookidoo Einkaufsliste (Quelle)**: z.B. `todo.cookidoo_einkaufsliste`
   - **Google Keep Liste (Ziel)**: z.B. `todo.google_keep_einkaufen`
   - **Conversation Agent** *(optional)*: z.B. `conversation.claude`
   - **LLM-Fallback aktivieren**: empfohlen ✅
3. Nach Bestätigung wird automatisch die Todo-Liste **`todo.cookidoo_keep_kategorien`** mit Default-Kategorien angelegt.

### ⚠️ Wichtig: Kategorien-Reihenfolge anpassen

Die mitgelieferten Default-Kategorien (z.B. „Obst/Gemüse → Kartoffel/Zwiebel → … → Getränke") sind die Reihenfolge eines konkreten Rewe-Marktes — **die wirst du fast sicher anpassen wollen**. Mach das so:

1. **Übersicht → Todo → `Cookidoo Keep Kategorien`** öffnen
2. Items per Drag & Drop in die Reihenfolge bringen, in der du tatsächlich durch deinen Markt läufst
3. Items hinzufügen / entfernen wie gewohnt
4. Beim nächsten Sync gewinnt diese Reihenfolge

Du kannst diese Liste auch in Google Keep oder anderen Todo-Apps editieren, falls du deine Keep-Sync-Integration entsprechend konfiguriert hast — die Reihenfolge wird übernommen.

## Wie starte ich das Ding?

Die Integration legt **keinen automatischen Trigger** an — du entscheidest, wann synchronisiert werden soll. Drei empfohlene Wege:

### 1. Dashboard-Button (am einfachsten, „auf Knopfdruck")

Füge eine Button-Card in dein Dashboard ein:

```yaml
type: button
name: Einkauf sortieren
icon: mdi:cart-arrow-right
show_state: false
tap_action:
  action: perform-action
  perform_action: cookidoo_keep_sync.sync
```

Tippst du auf den Button: Sync läuft. Ideal direkt vor dem Einkaufen.

### 2. Automation: bei Änderung in Cookidoo automatisch syncen

Sobald Cookidoo neue Items in die Einkaufsliste schreibt (z.B. wenn ihr ein Rezept aufnehmt), läuft der Sync von selbst:

```yaml
alias: "Cookidoo→Keep auto-sync"
description: Synct, sobald sich die Cookidoo-Liste ändert
mode: single
max_exceeded: silent
trigger:
  - platform: state
    entity_id: todo.cookidoo_einkaufsliste
    # Debounce: nur triggern, wenn 30s lang nichts mehr passiert
    for: "00:00:30"
action:
  - service: cookidoo_keep_sync.sync
```

(`mode: single` plus die 30-Sekunden-Pause verhindert, dass bei Schnellfeuer-Änderungen mehrere Syncs gleichzeitig laufen.)

### 3. Zeitgesteuert (z.B. jeden Morgen vor dem Einkauf)

```yaml
alias: "Cookidoo→Keep täglich 09:00"
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: cookidoo_keep_sync.sync
```

### Per Sprachbefehl (Voice Assistant / Assist)

Wenn du **Claude (oder einen anderen Conversation-Agent)** als Assist-Pipeline nutzt und in der Pipeline „Service-Aufrufe erlauben" aktiviert ist:

> *„Sortier die Einkaufsliste"* → der Agent ruft `cookidoo_keep_sync.sync` auf.

Du kannst das Verhalten zuverlässiger machen, indem du eine **HA-Intent-Skript-Datei** dafür anlegst — siehe HA-Doku „Intent Scripts".

### Manuelles Testen

**Entwicklerwerkzeuge → Aktionen → `cookidoo_keep_sync.sync` → Aktion ausführen**

Aktiviere „Antwort zurückgeben", dann siehst du sofort, was hinzugefügt, abgehakt und gelernt wurde:

```yaml
added:
  - ["Obst/Gemüse", "Tomaten"]
  - ["Fleisch", "Hähnchenbrust"]
completed_in_cookidoo:
  - "Tomaten"
  - "Hähnchenbrust"
learned:
  hähnchenbrust: "Fleisch"
```

## Wie läuft ein Sync ab?

```
1. Lese alle OFFENEN (nicht abgehakten) Items aus
     - der Cookidoo-Liste
     - der Google-Keep-Liste
   und mergen sie in eine deduplizierte Gesamtliste.

2. Klassifizieren:
     a) Keyword-Match (offline, instant)         → Obst/Gemüse
     b) Bei Miss: Bulk-LLM-Call (ein Call für    → "[N] Kategoriename"
        ALLE Restartikel, geparst per Regex)
     c) Sonst: Kategorie "Sonstiges"
   Jedes vom LLM klassifizierte Item wird persistent gelernt.

3. Sortieren nach Kategorie-Reihenfolge aus
     todo.cookidoo_keep_kategorien
   (Drag & Drop in der HA-UI), innerhalb einer Kategorie alphabetisch.

4. Alle offenen Keep-Items löschen, sortierte Liste neu schreiben.
   Bereits abgehakte Keep-Items bleiben unangetastet.

5. Cookidoo-Items, die wir kopiert haben, in Cookidoo abhaken
   → kein Doppel-Import beim nächsten Sync.
```

Beim nächsten Sync werden gelernte Items per Keyword-Match aufgelöst — der LLM wird nur für **wirklich neue** Items befragt. So kostet ein Sync mit 30 bekannten + 2 neuen Items genau einen Bulk-Call.

## Konfigurationsoptionen

**Einstellungen → Geräte & Dienste → Cookidoo → Keep → Konfigurieren**

| Bereich | Was du dort einstellst |
|---------|------------------------|
| **Listen & Agent** | Quell-/Ziel-Todo-Listen, Conversation-Agent, optionaler Override für die Kategorien-Liste |
| **Keyword-Mappings** | Eigene `keyword = Kategorie`-Zeilen ergänzen (überschreibt Defaults) |
| **Erweitert** | Keep-Liste vor jedem Sync komplett leeren (Vorsicht!) |

Die **Kategorien-Reihenfolge** wird **nicht** hier gepflegt, sondern direkt in der Todo-Entity (siehe oben).

## Services

| Service | Beschreibung |
|---------|--------------|
| `cookidoo_keep_sync.sync` | Vollständiger Sync. Optional Parameter `entry_id` (bei mehreren Konfigurationen). Liefert eine `response` mit `added`, `skipped`, `learned`. |
| `cookidoo_keep_sync.reset_learned` | Löscht den LLM-Lern-Cache (z.B. wenn du Kategorien umbenannt hast). |

## Datenschutz / Privacy

- Items werden nur an den **bei dir konfigurierten** Conversation-Agent gesendet.
- Wenn du **lokales LLM** willst (z.B. Ollama), wähle entsprechend bei „Conversation Agent".
- Keine Telemetrie, keine externen Aufrufe außer die durch den Conversation-Agent.

## Troubleshooting

**„Keine Items in Keep nach Sync"**: Prüfe Logs (`Settings → System → Logs`, Filter `cookidoo_keep_sync`). Häufigste Ursache: falsche Entity-IDs oder Keep-Sync-Integration kann (noch) nicht schreiben.

**„LLM klassifiziert in nicht-existente Kategorie"**: Der LLM gibt manchmal einen Namen aus, der nicht exakt einer deiner Kategorien entspricht. Die Integration mappt fuzzy (Substring-Match), wenn auch das fehlschlägt landet das Item in „Sonstiges". Lösung: passende Keyword-Regel ergänzen ODER Kategoriename leicht anpassen.

**„Reihenfolge in Keep stimmt nicht"**: Die Keep-Sync-Integration übernimmt die Add-Reihenfolge je nach Version unterschiedlich. Falls die Sortierung dort nicht erhalten bleibt, aktiviere im Erweitert-Tab „Keep-Liste vor jedem Sync komplett leeren".

## Limitierungen

- Synct **nur in eine Richtung** (Cookidoo → Keep). Was du in Keep abhakst oder hinzufügst, geht nicht zurück nach Cookidoo (das ist auch gar nicht möglich, Cookidoo ist read-only).
- Duplikat-Erkennung erfolgt per **case-insensitivem Summary-Vergleich** — geringfügig unterschiedliche Schreibweisen werden als zwei verschiedene Items behandelt.

## Beitragen

PRs willkommen — insbesondere für:
- Bessere Default-Kategorien für andere Märkte
- Weitere Keyword-Mappings (gerne als PR mit Region/Markt-Notiz)
- Übersetzungen

## Lizenz

MIT — siehe [LICENSE](LICENSE)

## Credits

- [miaucl/ha-cookidoo](https://github.com/miaucl/ha-cookidoo) für die Cookidoo-Integration
- [watkins-matt/home-assistant-google-keep-sync](https://github.com/watkins-matt/home-assistant-google-keep-sync) für die Google-Keep-Integration
- Anthropic für Claude (für „warum liegt da Spätzle nicht bei den Nudeln")
