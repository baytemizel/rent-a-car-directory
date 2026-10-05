#!/usr/bin/env python3
"""Ham tarama sonuçlarını (data/ham/osm/*.json) ve elle girilen kayıtları
(data/manuel.csv) birleştirip il il liste dosyalarını üretir:

    data/iller/<plaka>-<il>.md   okunabilir tablo
    data/iller/<plaka>-<il>.csv  makine tarafından okunabilir
    data/tum-firmalar.csv        tüm iller tek dosyada
    data/README.md               il bazında özet / dizin

Kullanım:
    python3 scripts/olustur.py
"""

import csv
import json
import re
from pathlib import Path

from iller import ILLER, dosya_adi

KOK = Path(__file__).resolve().parent.parent
HAM_DIZIN = KOK / "data" / "ham" / "osm"
MANUEL_CSV = KOK / "data" / "manuel.csv"
IL_DIZIN = KOK / "data" / "iller"

ALANLAR = ["firma_adi", "yetkili", "telefon", "website", "email", "ilce", "adres", "kaynak"]
MANUEL_ALANLAR = ["il_plaka"] + ALANLAR


def ilk(etiketler: dict, *anahtarlar: str) -> str:
    for anahtar in anahtarlar:
        deger = etiketler.get(anahtar, "").strip()
        if deger:
            return deger
    return ""


def osm_kaydi(eleman: dict) -> dict | None:
    t = eleman.get("tags", {})
    ad = ilk(t, "name", "name:tr", "brand", "operator")
    if not ad:
        return None
    sokak = " ".join(p for p in (t.get("addr:street", ""), t.get("addr:housenumber", "")) if p)
    adres = ", ".join(p for p in (sokak, t.get("addr:neighbourhood", ""), t.get("addr:postcode", "")) if p)
    return {
        "firma_adi": ad,
        "yetkili": ilk(t, "contact:person", "contact:name"),
        "telefon": " / ".join(dict.fromkeys(
            p for p in (ilk(t, "phone", "contact:phone"), ilk(t, "mobile", "contact:mobile")) if p
        )),
        "website": ilk(t, "website", "contact:website", "url", "brand:website"),
        "email": ilk(t, "email", "contact:email"),
        "ilce": ilk(t, "addr:district", "addr:city", "addr:suburb"),
        "adres": adres,
        "kaynak": f"https://www.openstreetmap.org/{eleman['type']}/{eleman['id']}",
    }


def anahtar(kayit: dict) -> str:
    """Aynı firmanın tekrar eden kayıtlarını eşlemek için normalize isim+telefon."""
    ad = re.sub(r"[^0-9a-zçğıöşü]", "", kayit["firma_adi"].casefold())
    tel = re.sub(r"\D", "", kayit["telefon"])[-10:]
    return f"{ad}|{tel}"


def birlestir(mevcut: dict, yeni: dict) -> None:
    """Boş alanları yeni kayıttan doldurur; kaynakları biriktirir."""
    for alan in ALANLAR:
        if alan == "kaynak":
            kaynaklar = [k for k in (mevcut["kaynak"], yeni["kaynak"]) if k]
            mevcut["kaynak"] = " ".join(dict.fromkeys(" ".join(kaynaklar).split()))
        elif not mevcut[alan] and yeni[alan]:
            mevcut[alan] = yeni[alan]


def kayitlari_topla() -> dict[int, list[dict]]:
    il_kayitlari: dict[int, dict[str, dict]] = {p: {} for p in ILLER}

    # Elle girilen kayıtlar önceliklidir (yetkili vb. bilgiler buradan gelir).
    if MANUEL_CSV.exists():
        with MANUEL_CSV.open(encoding="utf-8") as f:
            for satir in csv.DictReader(f):
                plaka = int(satir["il_plaka"])
                kayit = {a: (satir.get(a) or "").strip() for a in ALANLAR}
                if not kayit["firma_adi"]:
                    continue
                kayit["kaynak"] = kayit["kaynak"] or "manuel"
                hedef = il_kayitlari[plaka]
                k = anahtar(kayit)
                if k in hedef:
                    birlestir(hedef[k], kayit)
                else:
                    hedef[k] = kayit

    for plaka in ILLER:
        ham = HAM_DIZIN / f"{dosya_adi(plaka)}.json"
        if not ham.exists():
            continue
        hedef = il_kayitlari[plaka]
        for eleman in json.loads(ham.read_text(encoding="utf-8")).get("elements", []):
            kayit = osm_kaydi(eleman)
            if not kayit:
                continue
            k = anahtar(kayit)
            # Telefonsuz kopyaları da isim üzerinden yakala
            ad_eslesme = next((m for m in hedef if m.split("|")[0] == k.split("|")[0]
                               and (not k.split("|")[1] or not m.split("|")[1])), None)
            if k in hedef:
                birlestir(hedef[k], kayit)
            elif ad_eslesme:
                birlestir(hedef[ad_eslesme], kayit)
            else:
                hedef[k] = kayit

    return {
        p: sorted(kayitlar.values(), key=lambda r: r["firma_adi"].casefold())
        for p, kayitlar in il_kayitlari.items()
    }


def md_hucre(deger: str) -> str:
    return deger.replace("|", "\\|").replace("\n", " ")


def link(deger: str, tur: str) -> str:
    if not deger:
        return ""
    if tur == "website":
        url = deger if deger.startswith("http") else f"https://{deger}"
        return f"[{md_hucre(deger)}]({url})"
    if tur == "email":
        return f"[{md_hucre(deger)}](mailto:{deger})"
    if tur == "kaynak":
        return " ".join(
            f"[OSM]({k})" if "openstreetmap.org" in k else
            (f"[link]({k})" if k.startswith("http") else md_hucre(k))
            for k in deger.split()
        )
    return md_hucre(deger)


def il_md(plaka: int, kayitlar: list[dict]) -> str:
    il = ILLER[plaka]
    satirlar = [
        f"# {il} ({plaka:02d}) — Rent a Car Firmaları",
        "",
        f"Toplam **{len(kayitlar)}** kayıt. "
        "Kaynak: OpenStreetMap (ODbL) ve elle doğrulanmış kayıtlar (`data/manuel.csv`).",
        "",
    ]
    if not kayitlar:
        satirlar.append("_Bu il için henüz kayıt yok. Tarama çalıştırın veya `data/manuel.csv` dosyasına ekleyin._")
        return "\n".join(satirlar) + "\n"
    satirlar += [
        "| # | Firma | Yetkili | Telefon | Website | E-posta | İlçe | Adres | Kaynak |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(kayitlar, 1):
        satirlar.append("| " + " | ".join([
            str(i), md_hucre(r["firma_adi"]), md_hucre(r["yetkili"]), md_hucre(r["telefon"]),
            link(r["website"], "website"), link(r["email"], "email"),
            md_hucre(r["ilce"]), md_hucre(r["adres"]), link(r["kaynak"], "kaynak"),
        ]) + " |")
    return "\n".join(satirlar) + "\n"


def main():
    IL_DIZIN.mkdir(parents=True, exist_ok=True)
    tum = kayitlari_topla()
    ozet = []
    with (KOK / "data" / "tum-firmalar.csv").open("w", encoding="utf-8", newline="") as f_tum:
        tum_yazici = csv.DictWriter(f_tum, fieldnames=["il_plaka", "il"] + ALANLAR)
        tum_yazici.writeheader()
        for plaka in sorted(tum):
            kayitlar = tum[plaka]
            ad = dosya_adi(plaka)
            (IL_DIZIN / f"{ad}.md").write_text(il_md(plaka, kayitlar), encoding="utf-8")
            with (IL_DIZIN / f"{ad}.csv").open("w", encoding="utf-8", newline="") as f:
                yazici = csv.DictWriter(f, fieldnames=ALANLAR)
                yazici.writeheader()
                yazici.writerows(kayitlar)
            for r in kayitlar:
                tum_yazici.writerow({"il_plaka": plaka, "il": ILLER[plaka], **r})
            ozet.append((plaka, ad, len(kayitlar),
                         sum(bool(r["telefon"]) for r in kayitlar),
                         sum(bool(r["website"]) for r in kayitlar),
                         sum(bool(r["email"]) for r in kayitlar),
                         sum(bool(r["yetkili"]) for r in kayitlar)))

    toplam = [sum(o[i] for o in ozet) for i in range(2, 7)]
    satirlar = [
        "# İl Bazında Özet",
        "",
        "Bu dosya `scripts/olustur.py` tarafından otomatik üretilir; elle düzenlemeyin.",
        "",
        "| Plaka | İl | Firma | Telefonlu | Websiteli | E-postalı | Yetkili bilgili |",
        "|---|---|---|---|---|---|---|",
    ]
    for plaka, ad, *sayilar in ozet:
        satirlar.append(f"| {plaka:02d} | [{ILLER[plaka]}](iller/{ad}.md) | " + " | ".join(map(str, sayilar)) + " |")
    satirlar.append("| | **Toplam** | " + " | ".join(f"**{s}**" for s in toplam) + " |")
    (KOK / "data" / "README.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f"{toplam[0]} firma, {sum(1 for o in ozet if o[2])} ilde listelendi.")


if __name__ == "__main__":
    main()
