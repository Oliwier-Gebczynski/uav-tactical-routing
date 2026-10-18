# Narzędzia Python

```text
python/
├── main.py                   jeden punkt uruchamiania
├── uav_routing/
│   ├── __main__.py            wybór narzędzia
│   ├── paths.py               ścieżki projektu
│   ├── gui/mission_control.py aplikacja desktopowa
│   ├── maps/osm_importer.py   import OSM i NMT
│   ├── scenarios/model.py     model i walidacja scenariusza
│   └── visualization/         samodzielne wizualizatory
├── tests/                     testy oraz wspólne dane w fixtures.py
├── requirements/
│   ├── base.txt               GUI i wizualizacje
│   └── map-import.txt         biblioteki GIS
└── venv/                      lokalne środowisko, bez zmian
```

Komendy z katalogu głównego repozytorium:

```bash
python/venv/bin/python python/main.py                           # GUI
python/venv/bin/python python/main.py gui --map data/maps/gliwice_centrum.json
python/venv/bin/python python/main.py import-map --help
python/venv/bin/python python/main.py view perlin
python/venv/bin/python python/main.py dashboard perlin --save /tmp/dashboard.png
python/venv/bin/python python/main.py benchmark --save /tmp/benchmark.png
```

Z katalogu `python` można użyć `venv/bin/python -m uav_routing gui` i tych
samych podkomend. Importer i jego pomoc nie ładują GUI ani biblioteki Qt.
Wizualizatory odnajdują dane projektu także przy uruchomieniu z innego katalogu.
Względna ścieżka do istniejącego pliku użytkownika ma pierwszeństwo przed ścieżką
względem repozytorium. Domyślna pamięć podręczna importera znajduje się zawsze
w `data/cache/map-import` w repozytorium.

Instalacja zależności i testy, z katalogu głównego:

```bash
python/venv/bin/python -m pip install -r python/requirements/base.txt -r python/requirements/map-import.txt
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/uav-matplotlib \
  python/venv/bin/python -m unittest discover -s python/tests -t python -v
```

Wyniki, mapy i scenariusze pozostają w `data/`. Dawny obraz
`python/benchmark_summary.png` znajduje się teraz w `data/reports/benchmark_summary.png`.
Szczegóły: [GUI](../docs/mission-control.md), [mapy Polski](../docs/polskie-mapy.md).
