"""
Tartu 1914 aadresside puhastamine ja geokodeerimine Maa-ameti In-ADS API kaudu.

Kasutamine:
    python3 geocode.py aadressid.tsv tulemused.csv

Sisendformaat (TSV, ilma päiseta): tänav <TAB> number
Väljund (CSV): vt allpool.

Staatused:
  ok            — täpne unikaalne vaste
  multiple      — mitu vastet (võetud esimene, vaja kontrollida)
  not_found     — ei leitud
  manual_needed — aadress puhastusreeglite järgi ebakindel
  error         — võrgu- või parsimisviga
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict, Counter


# Vanade tänavanimede kaardistus tänapäevasteks Tartu nimedeks.
# Põhineb Vikipeedia loendil, Karlova miljööala dokumendil ja muudel allikatel.
# Veerg 4 (kindlus) tabeli põhjal — vt Tartu_1914_tanavanimed_kontrollimiseks.xlsx
TANAV_VANA_UUS = {
    # Kindlad muutused
    "Elisabeti":      "Eha",            # Karlovas, ümber nim 14.05.1936
    "Kompani":        "Kompanii",       # ortograafia
    "Peterburi":      "Narva mnt",      # 1927 nimemuutus
    "Petrogradi":     "Narva mnt",      # I MS ajal Peterburi → Petrogradi
    "Suurturg":       "Raekoja plats",  # Großer Markt
    "Valeria":        "Linda",          # Karlova 1909 plaan
    # Tõenäolised
    "Hetseli":        "J. W. F. Hezeli",
    "J. Hurda":       "Jakob Hurda",
    # Topelt-kirjapilt
    "Riia mnt":       "Riia",
    "õnne":           "Õnne",
}

# Tänavad, mille puhul mapping pole kindel — geokodeerimine ebatäpne
KAHTLASED = {
    "Magasini":   "Vabaduse pst",    # võib olla osaliselt teine tn
    "Promenaadi": None,              # asukoht ebaselge
    "Söögiturg":  "Küüni",            # võib olla Raekoja plats
    "Vladimiri":  None,              # kaks erinevat Vladimirit ajaloos
}


def normaliseeri_number(num: str) -> str:
    """Normaliseerib majanumbri: '77-a' → '77a', '9 // 11' → '9'"""
    if not num or not num.strip():
        return ""
    num = num.strip()
    if "//" in num:
        num = num.split("//")[0].strip()
    num = num.replace("-", "").replace(" l", "").replace(" ", "")
    return num


def normaliseeri_tanav(tanav: str) -> tuple[str, str]:
    """
    Tagastab (paringuks_kasutatav_nimi, marka).
    Tühi paringuks_kasutatav_nimi tähendab "ära proovi automaatselt".
    """
    t = tanav.strip()

    if t in KAHTLASED:
        uus = KAHTLASED[t]
        if uus is None:
            return ("", f"vana nimi '{t}' — asukoht ebaselge, vajab käsitsi paigutust")
        return (uus, f"KAHTLANE mapping: '{t}' → '{uus}' (kontrollida)")

    if t in TANAV_VANA_UUS:
        uus = TANAV_VANA_UUS[t]
        return (uus, f"vana nimi '{t}' → '{uus}'")

    return (t, "")


def geocode_inads(aadress_tekst: str) -> dict:
    """Päring Maa-ameti In-ADS geokodeerimise API vastu."""
    params = {
        "address": aadress_tekst,
        "results": 5,
        "appartment": 0,
        "unik": 0,
    }
    url = (
        "https://inaadress.maaamet.ee/inaadress/gazetteer"
        "?" + urllib.parse.urlencode(params)
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "tartu-1914-geocoder/0.2"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parsi_vaste(vaste: dict) -> dict:
    """Eraldab vastest koordinaadid ja võtmeväljad."""
    return {
        "x_lest":  vaste.get("viitepunkt_x") or vaste.get("X") or "",
        "y_lest":  vaste.get("viitepunkt_y") or vaste.get("Y") or "",
        "lat":     vaste.get("viitepunkt_b") or vaste.get("latitude") or "",
        "lon":     vaste.get("viitepunkt_l") or vaste.get("longitude") or "",
        "ads_oid": vaste.get("ads_oid") or "",
        "aadress_taielik": vaste.get("pikkaadress") or vaste.get("aadresstekst") or "",
    }


def tootle(sisend_tsv: str, valjund_csv: str):
    with open(sisend_tsv, encoding="utf-8") as f:
        read = [r.rstrip("\n").split("\t") for r in f if r.strip()]

    # Dedupleerime unikaalsete aadresside kaupa, säilitades esinemiste arvu
    unik = OrderedDict()
    for rea in read:
        if len(rea) < 2:
            tanav, number = rea[0], ""
        else:
            tanav, number = rea[0], rea[1]
        v = (tanav.strip(), number.strip())
        unik[v] = unik.get(v, 0) + 1

    print(f"Loetud {len(read)} rida, unikaalseid aadresse {len(unik)}",
          file=sys.stderr)

    valjund_read = []
    for i, ((tanav, number), kogus) in enumerate(unik.items(), 1):
        number_n = normaliseeri_number(number)
        tanav_n, marka = normaliseeri_tanav(tanav)

        rida = {
            "tanav_algne": tanav,
            "number_algne": number,
            "tanav_norm": tanav_n,
            "number_norm": number_n,
            "esinemisi": kogus,
            "aadress_paring": "",
            "x_lest": "", "y_lest": "", "lat": "", "lon": "",
            "staatus": "", "vasted_arv": 0, "ads_oid": "",
            "aadress_taielik": "",
            "marka": marka,
        }

        if not tanav_n:
            rida["staatus"] = "manual_needed"
            valjund_read.append(rida)
            continue

        paring = f"Tartu linn, {tanav_n} {number_n}".strip().rstrip(",")
        rida["aadress_paring"] = paring

        try:
            vastus = geocode_inads(paring)
            vasted = vastus.get("addresses") or []
            rida["vasted_arv"] = len(vasted)
            if not vasted:
                rida["staatus"] = "not_found"
            else:
                parsed = parsi_vaste(vasted[0])
                rida.update(parsed)
                rida["staatus"] = "ok" if len(vasted) == 1 else "multiple"
        except Exception as e:
            rida["staatus"] = "error"
            rida["marka"] = (rida["marka"] + f" | viga: {e}").strip(" |")

        valjund_read.append(rida)
        if i % 20 == 0:
            print(f"  {i}/{len(unik)}…", file=sys.stderr)
        time.sleep(0.15)  # viisakas päringutempo

    veerud = [
        "tanav_algne", "number_algne", "tanav_norm", "number_norm",
        "esinemisi", "aadress_paring", "x_lest", "y_lest", "lat", "lon",
        "staatus", "vasted_arv", "ads_oid", "aadress_taielik", "marka",
    ]
    with open(valjund_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=veerud)
        w.writeheader()
        for r in valjund_read:
            w.writerow({k: r.get(k, "") for k in veerud})

    kokku = Counter(r["staatus"] for r in valjund_read)
    print("\nKokkuvõte:", file=sys.stderr)
    for s, n in kokku.most_common():
        print(f"  {s}: {n}", file=sys.stderr)
    print(f"\nVäljund: {valjund_csv}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kasutamine: python3 geocode.py sisend.tsv valjund.csv",
              file=sys.stderr)
        sys.exit(1)
    tootle(sys.argv[1], sys.argv[2])
