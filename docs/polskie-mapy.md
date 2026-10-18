# Mapy Polski: OSM + NMT

Drugi sposób tworzenia mapy pobiera obiekty z OpenStreetMap i wysokość gruntu
z usługi WCS NMT GUGiK. Generator Perlina nadal działa jak wcześniej.

## Pierwsza mapa: centrum Gliwic

Z katalogu głównego projektu:

```bash
python/venv/bin/python -m pip install -r python/requirements/map-import.txt
python/venv/bin/python python/main.py import-map \
  --center 50.2945 18.6657 --size 200 200 \
  --output data/maps/gliwice_centrum.json
```

`--center` przyjmuje **szerokość, długość geograficzną**, a `--size` szerokość
i wysokość obszaru w metrach. Wynik jest prostokątem w EPSG:2180. Limit wynosi
milion komórek; na początek zalecane są wycinki 200 × 200 m.

Kolejne uruchomienia korzystają z `data/cache/map-import/`. Opcja `--offline`
zabrania dostępu do sieci; brak odpowiedniego pliku w pamięci jest błędem.
Pamięć podręczna nie jest automatycznie odświeżana. Żeby pobrać nowy stan,
podaj nowy katalog przez `--cache-dir`. Odpowiedzi błędów WCS i niekompletne
odpowiedzi Overpass nie są zapisywane jako poprawne dane.

Można też użyć własnych danych:

```bash
python/venv/bin/python python/main.py import-map \
  --center 50.2945 18.6657 --size 200 200 \
  --osm-file /sciezka/gliwice-overpass.json \
  --dem /sciezka/nmt.tif --offline \
  --output data/maps/gliwice_centrum.json
```

Plik OSM musi być odpowiedzią JSON Overpass z geometrią (`out geom`),
a NMT rastrem z georeferencją obejmującym cały wycinek. Raster innego układu
poziomego jest przeliczany na EPSG:2180. Braki NoData powodują błąd importu.
Importer nie przelicza układu wysokościowego; nie należy łączyć NMT i innych
danych wysokościowych bez sprawdzenia ich zgodności. Używaj NMT gruntu,
nie NMPT zawierającego już budynki i drzewa.

## Odczyt w C++ i podgląd

```bash
cmake -S . -B build
cmake --build build -j 4
./build/UAVPlanner --map data/maps/gliwice_centrum.json \
  --output data/maps/gliwice_loaded.json
python/venv/bin/python python/main.py view data/maps/gliwice_loaded.json
```

`--map` w tym etapie wczytuje, sprawdza i eksportuje teren. Nie tworzy misji,
radarów ani wyników optymalizacji. W kodzie `JsonMapImporter::load(filename)`
zwraca zwykły `Map`, który można przekazać do istniejącej symulacji.
Uruchomienie programu bez argumentów nadal wykonuje scenariusze proceduralne.
Podgląd terenu jest dostępny również bez uruchamiania C++ bezpośrednio z JSON
wygenerowanego przez importer.

## Model wysokości i obiektów

- `groundElevation`: wysokość gruntu w metrach w układzie źródła NMT.
- `obstacleHeight`: wysokość przeszkody ponad gruntem danej komórki.
- `elevation`: wysokość górnej powierzchni, czyli suma tych dwóch wartości.
  To pole zachowuje zgodność z istniejącym plannerem i wizualizatorami.
- `buildingId`: identyfikator OSM wskazujący rekord w `metadata.buildings`.
- `landCoverKnown`: czy typ pokrycia wynika z obsługiwanych obiektów OSM.
  Nieznane pokrycie jest tymczasowo reprezentowane jako `Grass`.

Jedna komórka odpowiada **1 × 1 m**, bo obecny planner używa indeksów siatki
jako odległości w metrach. Punkt `(0, 0)` to środek północno-zachodniej komórki;
x rośnie na wschód, y na południe. `metadata.bounds` zawiera granice zewnętrzne
siatki `[west, south, east, north]` w EPSG:2180. Aby przeliczyć indeks punktu:
`E = west + x + 0.5`, `N = north - y - 0.5`.

Wysokość budynku pochodzi kolejno z:

1. `height` — uwzględnia już dach; obsługiwane są metry, stopy i zapis stopy/cale.
2. `building:levels × 3 m` plus `roof:height`, następnie `roof:levels × 3 m`,
   a przy braku obu domyślnie 2 m dachu lub 0 m dla dachu płaskiego.
3. Typu: dom 8 m, budynek wielorodzinny 15 m, garaż/szopa 3 m, hala 9 m.
4. Wartości dla nieznanego budynku, domyślnie 12 m:
   `--unknown-building-height 18` zmienia to założenie.

Pozycje 2–4 są **założeniami symulacji**, nie pomiarami. Nie ma wiarygodnej
klasyfikacji domu i bloku na podstawie samego `building=yes`. Każdy rekord
budynku zapisuje `heightSource` i `estimated`. Obrysy pobierane przez granicę
wycinka są przycinane; podstawa takiego budynku jest szacowana tylko z części
widocznej w wycinku. Budynek otrzymuje stałą wysokość dachu względem najniższego
próbkowanego gruntu w obrysie. Dach nie może znaleźć się poniżej gruntu.

Obsługiwane są dziedzińce multipolygonów oraz `building:part`. Części nadpisują
wysokość obrysu we własnym obszarze; w nakładających się częściach wygrywa
najwyższa powierzchnia. Poza częściami zachowywany jest obrys jako uzupełnienie
niekompletnych danych. Tagi wysokości są odczytywane z danej części, bez
automatycznego dziedziczenia tagów z obrysu.

Lasy mają domyślnie 12 m (`--forest-height`). Linie dróg i cieków otrzymują
szerokość z tagu `width` albo wartość zastępczą. Priorytet pokrycia to budynek,
droga, woda, las, trawa. Rasteryzacja obejmuje każdą komórkę dotkniętą obiektem.

Obecny model jest mapą 2,5D: nie odwzorowuje przestrzeni pod mostami lub
nadwieszonymi budynkami, dachów o zmiennym kształcie ani wielu przeszkód na
różnych wysokościach tej samej komórki. Obiekty oznaczone jako tunele są pomijane,
a pozostałe obiekty nadziemne traktowane jako pełne kolumny do gruntu. Kolejnym
rozszerzeniem może być uzupełnianie wysokości modelami 3D budynków GUGiK;
ten etap ich jeszcze nie importuje.

## Sprawdzenie zmian

```bash
python/venv/bin/python -m unittest discover -s python/tests -t python -p 'test_import_osm_map.py' -v
ctest --test-dir build --output-on-failure
```

Testy obejmują dobór wysokości, dachy i jednostki, płaski dach na zboczu,
części budynków, dziedzińce, priorytety pokrycia, orientację rastra, braki NMT,
pracę offline i walidację formatu po stronie C++.

## Źródła

- [GUGiK — usługi pobierania WCS](https://www.geoportal.gov.pl/pl/usluga/uslugi-pobierania-wcs/)
- [OSM — wysokość](https://wiki.openstreetmap.org/wiki/Key:height)
- [OSM — kondygnacje](https://wiki.openstreetmap.org/wiki/Key:building:levels)
- [OSM — budynki 3D](https://wiki.openstreetmap.org/wiki/Simple_3D_buildings)
- [OSM — atrybucja i licencja ODbL](https://www.openstreetmap.org/copyright)

Wynik zapisuje atrybucję OpenStreetMap i GUGiK oraz odnośnik do licencji OSM
w metadanych. Pliki wygenerowanych map i pamięć podręczna są pomijane przez Git.
