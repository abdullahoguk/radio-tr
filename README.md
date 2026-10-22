# radio-tr

Türkiye radyolarını listeleyip dinleyebildiğin, minimal İsviçre tipografisiyle tasarlanmış bir PWA.

- İstasyon verisi: [Radio Browser](https://www.radio-browser.info/) API (`countrycode=TR`), 12 saat yerel önbellek
- Arama, tür filtreleri, favoriler, kaldığın istasyonu hatırlama
- Tam ekran oynatıcı (kadran + ibre), Media Session (kilit ekranı / klavye medya tuşları), HLS desteği
- Kısayollar: `/` ara, `Boşluk` oynat/duraklat, `←` `→` önceki/sonraki
- Kurulabilir PWA, uygulama kabuğu çevrimdışı çalışır

## Çalıştırma

Derleme adımı yok; uygulama `public/` klasöründe, herhangi bir statik sunucu yeterli:

```sh
python3 -m http.server 8765 -d public
```

HTTPS üzerinde yayınlandığında tarayıcı `http://` akışları engellediği için bu istasyonlar listede gizlenir.

## Yayınlama

Cloudflare Workers (statik varlıklar) için `wrangler.jsonc` hazır. Build komutu boş kalır, deploy komutu `npx wrangler deploy`.
