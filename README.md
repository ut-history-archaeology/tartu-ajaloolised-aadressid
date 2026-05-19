# Tartu 1914 aadresside kaardile paigutamine

Tööriist Tartu aadresside paigutamiseks ja kontrollimiseks Maa-ameti ajalooliste linnaplaanide peal (1914, 1927, 1938). Rakendus töötab brauseris, vajamata serverit.

## Sisu

- [`kaart.html`](kaart.html) — brauseripõhine kaardirakendus
- [`tulemused.csv`](tulemused.csv) — geokodeeritud demo-aadresside lähteandmed
- [`geocode.py`](geocode.py) — Pythoni skript, millega `tulemused.csv` genereeriti

## Andmetöötlus

Demoaadressid sisaldavad ~700 aadressikirjet kujul `tänav <tab> majanumber`. Enne geokodeerimist viidi sisse järgmised muudatused.

### Tänavanimede ajalooline kaardistus

Geokodeerimise jaoks kaardistati vanad nimed tänapäeva omadega. Allikateks olid Tartu tänavate

**Muudatused**

| Algne nimi | Muudetud kujule |
| ---------- | --------------- |
| Elisabeti  | Eha             |
| Kompani    | Kompanii        |
| Peterburi  | Narva mnt       |
| Petrogradi | Narva mnt       |
| Suurturg   | Raekoja plats   |
| Valeria    | Linda           |
| Hetseli    | J. W. F. Hezeli |
| J. Hurda   | Jakob Hurda     |
| Magasini   | Vabaduse pst    |
| Söögiturg  | Küüni           |
| Riia mnt   | Riia            |
| õnne       | Õnne            |

### Geokodeerimise tulemus

Iga aadress päringuti Maa-ameti In-ADS aadressiteenuse vastu. Skript `geocode.py` lisas iga reale staatuse:

- **ok** — leitud üks unikaalne vaste, koordinaadid usaldusväärsed
- **multiple** — leitud mitu vastet, võetud esimene (vajab kontrolli)
- **not_found** — ei leitud
- **manual_needed** — tänav märgitud ebakindlaks, automaatset päringut ei tehtud
- **error** — võrgu- või parsimisviga

## Kaardirakendus

[`kaart.html`](kaart.html) on brauseripõhine rakendus aadresside kaardile paigutamiseks ja kontrollimiseks.

### Avamine

Lae fail alla ja ava brauseris (topelt-klõps). Internetiühendus on vajalik Maa-ameti WMS-teenusele ja Leafleti CDN-ile.

### Tausta-kihid

Kaardil saab vahetada nelja tausta-kihti (parem ülanurk):

- **OSM** — tänapäev (OpenStreetMap)
- **Tartu 1914** — Maa-ameti ajalooline linnaplaan, mõõtkavas 1:600 (kõige detailsem)
- **Tartu 1927** — Maa-ameti ajalooline linnaplaan
- **Tartu 1938** — Maa-ameti ajalooline linnaplaan

### Kategooriad

Iga aadressile saab määrata ühe kolmest kategooriast. Värvid kehtivad nii kaardimarkeritel kui sidebar'i nimekirjas.

- 🔵 **Kontrollimata** (sinine) — vaikeolek, kui CSV laetakse esmakordselt sisse
- 🟢 **Kinnitatud** (roheline) — kasutaja vaatas üle ja koordinaat on õige
- 🟡 **Kahtlane** (kollane) — kasutaja pole kindel, vajab veel kontrolli

Valitud aadressi marker on suurem ja kannab kategooria värvi.

### Töövoog

1. **Lae CSV.** Klõpsa vasakul üleval **Choose file** ja vali `tulemused.csv`. Kõik aadressid tulevad sisse „kontrollimata“ olekus.
2. **Vali aadress.** Klõpsa nimekirjas — kaart liigub punkti juurde (kui koordinaat olemas) ning detailipaneel avaneb all.
3. **Kontrolli kaardil.** Vaata, kas punkt on 1914 (või 1927/1938) plaanil õiges kohas. Lülita kihte vajadusel.
4. **Märgista kategooria.** Klõpsa detailipaneelis ühel kolmest nupust.
5. **Lisa kommentaar.** Tekstiväljale saab kirjutada allikad, kahtluse põhjuse vms.
6. **Paranda koordinaat (vajadusel).** Kui punkt on vales kohas või puudub: vali aadress nimekirjast → **parem-klõps** kaardile õiges kohas → koordinaat salvestub.
7. **Salvesta progress.** Kasuta nuppu **Salvesta CSV**, et töö pooleli jätta. Tagasi tulles laed sama faili uuesti sisse — kategooriad ja kommentaarid säilivad.
8. **Ekspordi GeoJSON.** Lõppfaas — saad standardse WGS84 GeoJSON-i, mida saab kasutada QGIS-is, Mapboxis, Leafletis jms.

### Filtrid

Sidebar'is on filtrid (kõik / kontrollimata / kinnitatud / kahtlane / pole koordinaate). Suurte andmemahtudega töötades aitab see fokusseerida — näiteks „pole koordinaate“ näitab kohe need read, mis vajavad käsitsi paigutust.

### Failistruktuur (CSV)

CSV peab sisaldama vähemalt veerge `tanav_algne`, `number_algne`, `lat`, `lon`. Rakendus lisab töö käigus täiendavalt veerud:

- `kategooria` — `pole` | `kinnitatud` | `kahtlane`
- `kommentaar` — vabatekstiline

Salvestamisel kirjutab rakendus kõik veerud välja, sealhulgas need, mille ta CSV-st sisse luges. Nii ei kao algandmed (`staatus`, `aadress_taielik`, jne).

### GeoJSON eksport

Eksport tagastab `FeatureCollection` standardses WGS84-s (EPSG:4326, CRS84). Iga `Feature` properties osas:

```json
{
  "tanav_algne": "Elisabeti",
  "number_algne": "25",
  "tanav_norm": "Eha",
  "number_norm": "25",
  "aadress_taielik": "Tartu linn, Eha tn 25",
  "kategooria": "kinnitatud",
  "kommentaar": "...",
  "esinemisi": 5
}
```
