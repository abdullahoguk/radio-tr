#!/bin/sh
# Normalise downloaded logos (.cache/logos_raw/<id>) into 160px square WebP files in public/logos/.
set -e
cd "$(dirname "$0")/.."
mkdir -p public/logos
for f in .cache/logos_raw/*; do
  id=$(basename "$f")
  convert "$f[0]" -strip -resize 160x160 -background "#ffffff" -gravity center -extent 160x160 \
    -flatten -quality 82 "public/logos/$id.webp"
done
