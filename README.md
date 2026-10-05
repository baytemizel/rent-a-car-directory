# Türkiye Rent a Car Firma Rehberi

Türkiye'deki araç kiralama (rent a car) firmalarının **il il** listesi:
firma adı, yetkili, telefon, website ve e-posta.

- İl özeti ve dizin: [`data/README.md`](data/README.md)
- İl listeleri: `data/iller/<plaka>-<il>.md` (tablo) ve `.csv`
- Tüm Türkiye tek dosyada: [`data/tum-firmalar.csv`](data/tum-firmalar.csv)

## Veri nasıl toplanıyor?

| Kaynak | Ne sağlar | Nasıl |
|---|---|---|
| [OpenStreetMap](https://www.openstreetmap.org) (Overpass API) | Firma adı, telefon, website, e-posta, adres, ilçe | `scripts/tara_osm.py` her il için `amenity=car_rental` / `shop=car_rental` etiketli ve adında "rent a car", "araç kiralama" vb. geçen işletmeleri çeker |
| `data/manuel.csv` | Yetkili kişi ve OSM'de eksik bilgiler | Elle eklenir; OSM kaydıyla aynı firma (isim + telefon) ise otomatik birleştirilir, manuel değer önceliklidir |

`scripts/olustur.py` iki kaynağı birleştirir, tekrar eden kayıtları ayıklar ve
`data/` altındaki tüm liste dosyalarını yeniden üretir. Liste dosyalarını elle
düzenlemeyin; değişiklikleri `data/manuel.csv`'ye yapıp scripti çalıştırın.

### Otomatik tarama (GitHub Actions)

`.github/workflows/tara.yml` taramayı GitHub üzerinde çalıştırır ve sonuçları
repoya commit eder:

- **Elle:** Actions → "Rent a car taraması" → *Run workflow* (isteğe bağlı olarak
  yalnızca bazı plakalar, ör. `34 6 35`)
- **Otomatik:** her ayın 1'inde

### Yerelde çalıştırma

Yalnızca Python 3.10+ gerekir, ek paket yoktur.

```bash
python3 scripts/tara_osm.py          # 81 il (~5-10 dk). Belirli iller: tara_osm.py 34 6 35
python3 scripts/olustur.py           # listeleri üret
```

## Elle kayıt ekleme

`data/manuel.csv` sütunları:

```
il_plaka,firma_adi,yetkili,telefon,website,email,ilce,adres,kaynak
34,Örnek Oto Kiralama,Ad Soyad,0212 000 00 00,https://ornek.com.tr,info@ornek.com.tr,Şişli,"Örnek Cd. No:1",https://ornek.com.tr/iletisim
```

`kaynak` sütununa bilginin alındığı sayfanın adresini yazın.

## Kapsam ve sınırlamalar

- **Kapsam:** OSM gönüllü katkıyla oluşturulur; özellikle büyük şehirler ve
  turistik bölgeler iyi, küçük ilçeler daha zayıf kapsanır. Türkiye'deki tüm
  firmaları (on binlerce yetki belgeli işletme) garanti etmez. Eksik firmaları
  `data/manuel.csv`'ye veya doğrudan OpenStreetMap'e ekleyerek kapsamı artırabilirsiniz.
- **Yetkili bilgisi:** OSM'de nadiren bulunur. Gerçek kişilere ait isim ve iletişim
  bilgileri KVKK kapsamında kişisel veridir; yalnızca firmanın kendisinin kamuya
  açık olarak yayımladığı (ör. web sitesindeki iletişim sayfası) bilgileri,
  kaynağıyla birlikte ekleyin ve silme taleplerini yerine getirin.
- **Lisans:** OSM kaynaklı veriler © OpenStreetMap katkıcıları,
  [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) lisanslıdır; bu
  verilerden türetilen listeler de aynı lisansla paylaşılmalıdır.
