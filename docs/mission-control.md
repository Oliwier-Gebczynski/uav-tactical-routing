# UAV Mission Control

Lokalna aplikacja PyQt5 łączy generowanie i przeglądanie map, edycję scenariuszy
oraz uruchamianie istniejącego planera C++ i analizę jego wyników.

## Uruchomienie

Z katalogu głównego projektu:

```bash
python/venv/bin/python -m pip install -r python/requirements/base.txt -r python/requirements/map-import.txt
cmake -S . -B build
cmake --build build -j 4
python/venv/bin/python python/main.py gui
```

Można od razu otworzyć istniejący plik:

```bash
python/venv/bin/python python/main.py gui --map data/maps/gliwice_centrum.json
```

W bieżącym katalogu roboczym przygotowany jest również przykładowy scenariusz
`data/scenarios/gliwice_demo.json` i wynik `data/runs/demo_gliwice/result.json`.
Wybierz je z biblioteki, żeby obejrzeć działający edytor i panele wynikowe.

Własne środowisko można utworzyć przez `python3 -m venv python/venv` przed
instalacją zależności. Aplikacja używa lokalnego `build/UAVPlanner`.

## Przebieg pracy

### 01 / Mapa

Wpisz szerokość i długość geograficzną środka, wymiary w metrach oraz nazwę.
Domyślny środek znajduje się w centrum Gliwic. „Generuj OSM + NMT” uruchamia
importer w osobnym procesie, więc okno pozostaje dostępne. Maksymalny rozmiar
w GUI wynosi 1000 × 1000 m, przy komórce 1 m. Pobieranie wymaga internetu;
powtórne pobrania tego samego obszaru korzystają z pamięci podręcznej.

Jeżeli nazwa już istnieje, nowa mapa otrzymuje osobną nazwę z datą i sufiksem;
poprzednia mapa nie jest nadpisywana. Dziennik na dole pokazuje postęp i błędy.
Przycisk „Anuluj zadanie” zatrzymuje proces pobierania lub symulacji.

Przełączaj pokrycie terenu, wysokość gruntu, wysokość powierzchni i wysokość
przeszkód. Aktualny widok można zapisać jako PNG. Mapy proceduralne z dawnych
scenariuszy także są obsługiwane, ale nie mają oddzielnej warstwy gruntu.

### 02 / Scenariusz

1. Wybierz „Dodaj radar” i docelową liczbę radarów. Każde kliknięcie mapy
   dodaje radar z aktualnym zasięgiem, wysokością anteny i siłą.
2. Przełącz narzędzie na „Ustaw start”, „Dodaj checkpoint” i „Ustaw koniec”.
   Checkpointy są obowiązkowe i są odwiedzane w kolejności dodania.
3. Obiekty usuwa się po zaznaczeniu na liście lub narzędziem „Usuń najbliższy
   obiekt”. „Cofnij” przywraca poprzednią zmianę, także zmiany parametrów lotu.
4. Ustaw wspólną wysokość lotu, seed oraz profil: Szybki, Standard lub Dokładny.
   „Z pliku” zachowuje dokładne parametry wczytanego scenariusza.
5. Zapisz scenariusz, a następnie uruchom symulację.

Pozycje i zasięgi są podane w metrach / indeksach siatki. x rośnie na wschód,
y na południe. Wyłącz narzędzie przesuwania lub powiększania Matplotlib przed
stawianiem obiektów. Zasięg rysowany wokół radaru to okrąg teoretyczny;
rzeczywiste pole z przesłanianiem przez teren jest obliczane podczas symulacji.

Scenariusz można zapisać także jako szkic z samymi radarami. Uruchomienie wymaga
startu i końca. Limit wynosi 100 radarów i 98 checkpointów. Limit radarów w polu
„Docelowa liczba radarów” ogranicza dodawanie, a nie automatycznie rozstawia
obiekty ani nie usuwa istniejących. Parametry obok narzędzia dotyczą nowych
radarów; istniejący radar można usunąć i dodać ponownie.

**Wysokość lotu zachowuje obecny model planera:** punkty trasy są interpolowane
nad górną powierzchnią mapy, łącznie z budynkami i drzewami. Nie jest to stały
pułap względem morza ani zaawansowany model dynamiki lotu. Wspólna wysokość
dotyczy całej misji. Mapa radarowa jest liczona dla tej samej wysokości.

### 03 / Wyniki

Przycisk „Tabela metryk” rozwija porównanie trasy prostej, Local Search, SA i SA+LS: koszt, długość,
zagrożenie, kolizje, liczbę punktów i wykonalność. Lista widoków przełącza:

- trasy wszystkich algorytmów na mapie;
- obliczone pole radarowe;
- profil wysokości;
- koszty algorytmów;
- zagrożenie efektywne;
- zbieżność optymalizacji;
- dziennik decyzji.

Wykresy można eksportować do PNG. Zmiana scenariusza nie zmienia historycznych
wyników; panel pokazuje wtedy informację, że wynik dotyczy poprzedniego stanu.

## Zapis i powtarzalność

Biblioteka po lewej wyświetla pliki z:

```text
data/maps/                    mapy
data/scenarios/               zapisane scenariusze
data/runs/<data_nazwa_id>/
    scenario.json             pełna migawka wejścia danego uruchomienia
    result.json               mapa, wyniki i oryginalne wejście misji
```

Dwukrotne kliknięcie otwiera plik. „Otwórz plik JSON…” obsługuje również pliki
spoza tych katalogów. Można przełączać się między zapisanymi mapami i wynikami;
przy niezapisanych zmianach edytor pyta przed ich odrzuceniem.

Scenariusz to **samodzielny JSON zawierający pełną mapę**, radary, oryginalną
misję, seed, parametry optymalizatora i wagi funkcji kosztu. Nie odwołuje się do
aktualnego stanu OSM i nie wymaga ponownego pobierania mapy. Każde uruchomienie
zachowuje osobny scenariusz i wynik. Dane użytkownika w powyższych katalogach
nie są dodawane automatycznie do Git.

Powtórzenie z tym samym scenariuszem i tą samą wersją programu w tym samym
środowisku daje identyczne wyniki. Przy zmianie kodu planera, kompilatora lub
biblioteki standardowej sekwencje losowania i arytmetyka mogą się różnić.
Sam seed bez utrwalenia mapy i konfiguracji nie zapewnia powtarzalności.

Można uruchomić zapisany scenariusz również bez GUI:

```bash
./build/UAVPlanner --scenario data/scenarios/moj_scenariusz.json \
  --output data/maps/wynik.json
```

Wynik także może być wejściem `--scenario`: pole `inputMission` zachowuje
oryginalne checkpointy, zamiast ponownie optymalizować punkty tranzytowe wyniku.

## Wydajność i testy

Import, odczyt i zapis plików oraz symulacja odbywają się poza główną obsługą
okna. Matplotlib rysuje podgląd maksymalnie około 900 pikseli na oś; pełna
siatka pozostaje dostępna dla obliczeń i zapisu. Obszary 1 km² mogą zużywać
znacznie więcej RAM niż 200 × 200 m; JSON pełnej mapy jest obszerny.
Pole radarowe na dużym obszarze z wieloma radarami może liczyć się długo.

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/uav-matplotlib \
  python/venv/bin/python -m unittest discover -s python/tests -t python -p 'test_*.py' -v
ctest --test-dir build --output-on-failure
```

Testy obejmują zapis i walidację scenariusza, niezmienność migawki, obowiązkowe
checkpointy, identyczne wyniki dwóch uruchomień i odtworzenie z pliku wynikowego,
edycję i cofanie w GUI, blokadę edycji podczas zadania, przełączanie warstw,
eksport PNG oraz pełny przebieg uruchomienia procesu C++ z GUI.
