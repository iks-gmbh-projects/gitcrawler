# Projektdaten zum Blogartikel "Wer weiß was? – Wissensmonopole mit Git-Metadaten identifizieren"

In diesem Repository befindet sich der Quellcode zum Blogartikel. Das Projekt kann dazu genutzt werden eigene
Repositories zu visualisieren, nachfolgend eine kurze Anleitung.

## Nutzung des Pythonscripts
Zunächst müssen die Projektdateien kopiert werden.
```
git clone
```

### 1. Paketabhängigkeiten installieren

Anschließend in den Projektordner wechseln und die für den Crawler notwendigen Pakete installieren

```bash
cd gitcrawler
pip install -r requirements.txt
```

### 2. Crawler ausführen

Der Crawler wird anschließend durch Ausführen der `crawl.py` gestartet.

```
python src/crawl.py <github-URL>
```
Der Crawler klont das unter <github-URL> angegebene Repository in den Ordner `temp` und erstellt anschließend die zur
Visualisierung notwendigen Dateien.

Abhängig von der Größe des Repositories kann dieser Vorgang einige Zeit in Anspruch nehmen.

### 3. Visualisierung betrachten

Die Visualisierung kann anschließend durch Öffnen der `index.html` betrachtet werden.
