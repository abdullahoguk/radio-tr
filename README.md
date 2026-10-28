# radio-tr

Türkiye radyolarını listeleyip dinleyebildiğin, minimal İsviçre tipografisiyle tasarlanmış bir PWA.

- Seçilmiş istasyon listesi depoda: `public/data/stations.json` + `public/logos/` (dış API yok)
- Arama, kategori ve yayın grubu filtreleri, favoriler, kaldığın istasyonu hatırlama
- Tam ekran oynatıcı (kadran + ibre), Media Session (kilit ekranı / klavye medya tuşları), HLS desteği
- Kısayollar: `/` ara, `Boşluk` oynat/duraklat, `←` `→` önceki/sonraki
- Kurulabilir PWA, uygulama kabuğu çevrimdışı çalışır

## Çalıştırma

Derleme adımı yok; uygulama `public/` klasöründe, herhangi bir statik sunucu yeterli:

```sh
python3 -m http.server 8765 -d public
```

## İstasyon verisi

Liste şu kaynaklardan derlendi; her yayın adresi test edilip yalnızca HTTPS üzerinden çalışanlar alındı:

- **TRT**: [radyo.trt.net.tr](https://radyo.trt.net.tr/kanallar) resmi oynatıcısındaki 13 kanal (TRT Kurdî hariç)
- **Karnaval**: [karnaval.com](https://karnaval.com) istasyon kataloğu (StreamTheWorld akışları)
- **Diğerleri**: [radyolar.net.tr](https://radyolar.net.tr/stations) popülerlik sırası, açıklama, şehir, frekans ve logolar

Kategoriler (`Türkçe Pop`, `Türk Halk Müziği`, `Türk Sanat Müziği`, `Dini`…) kaynak sitelerin etiketlerinden değil,
`scripts/build_stations.py` içindeki kurallar ve elle düzeltmelerle atanır. Kürtçe yayın yapan istasyonlar listeye alınmaz.

Listeyi yenilemek için (ham indirmeler `.cache/` klasörüne, git dışında):

```sh
python3 scripts/check_streams.py .cache/cand.json > .cache/results.json   # akış testi
python3 scripts/build_stations.py                                          # public/data/stations.json
./scripts/process_logos.sh                                                 # .cache/logos_raw → public/logos/*.webp
```

## Yayınlama

Cloudflare Workers (statik varlıklar) için `wrangler.jsonc` hazır. Build komutu boş kalır, deploy komutu `npx wrangler deploy`.
