#!/usr/bin/env bash
# Download the two books, their HTML editions and their LaTeX sources into data/raw/.
#
# Both books are by Allen B. Downey, Green Tea Press, CC BY-NC 3.0:
#   Think Python 2e  https://greenteapress.com/wp/think-python-2e/
#   Think Stats 2e   https://greenteapress.com/wp/think-stats-2e/
# The LaTeX comes from the author's GitHub repositories, pinned to the commits
# the results were produced with. Downloads resume, so re-running after a
# dropped connection continues where it stopped; files already verified are
# skipped. greenteapress.com can be slow (a few KB/s here), hence the retries.
set -euo pipefail

cd "$(dirname "$0")/.."
RAW=data/raw
mkdir -p "$RAW/html/thinkpython2" "$RAW/html/thinkstats2"

TP_COMMIT=bbe57aef0014f51cdb9cf43523210e075fb24da2
TS_COMMIT=ed53b15755e08fccfdac07af5e5aac76e4507731

fetch() {  # fetch URL DEST [SHA256]
  local url=$1 dest=$2 want=${3:-}
  if [[ -n $want && -f $dest ]] && echo "$want  $dest" | sha256sum -c --status 2>/dev/null; then
    echo "ok       $dest"
    return
  fi
  for attempt in $(seq 1 30); do
    if curl -sSL --fail -m 180 -C - -o "$dest" "$url"; then
      break
    fi
    echo "retry $attempt $url" >&2
    sleep 2
  done
  if [[ -n $want ]] && ! echo "$want  $dest" | sha256sum -c --status; then
    echo "checksum mismatch for $dest (the upstream file may have been updated)" >&2
    exit 1
  fi
  echo "fetched  $dest"
}

fetch https://greenteapress.com/thinkpython2/thinkpython2.pdf "$RAW/thinkpython2.pdf" \
  9d923cacf1b07e88a6314395a5afafae1aa01cd1aa0ce16b1851d38b18542487
fetch https://greenteapress.com/thinkstats2/thinkstats2.pdf "$RAW/thinkstats2.pdf" \
  272d5c33b81447227ac58d37e0343a2e9266714ed13702f1d5d0333c67660f02
fetch "https://raw.githubusercontent.com/AllenDowney/ThinkPython2/$TP_COMMIT/book/book.tex" \
  "$RAW/thinkpython2.tex" 2a575edefd82d754a1088b5e35cf69435a3b82b27f689e0771d633f2df1a1fc4
fetch "https://raw.githubusercontent.com/AllenDowney/ThinkStats2/$TS_COMMIT/book/book.tex" \
  "$RAW/thinkstats2.tex" 130799d64be4a303b26b438115411509ee3d00c30a24a14e0b533f65235dbeec

# HTML editions: one page per chapter. Pages past the last chapter return 404.
for book in thinkpython2 thinkstats2; do
  for n in $(seq -w 1 30); do
    dest="$RAW/html/$book/${book}0$n.html"
    [[ -s $dest ]] && continue
    code=$(curl -sSL -m 180 -o "$dest" -w '%{http_code}' \
      "https://greenteapress.com/$book/html/${book}0$n.html" || true)
    if [[ $code != 200 ]]; then
      rm -f "$dest"
      break
    fi
    echo "fetched  $dest"
  done
done
echo "done: $(ls "$RAW"/html/thinkpython2 | wc -l) + $(ls "$RAW"/html/thinkstats2 | wc -l) HTML pages"
# Every file the results were produced from, by hash.
if (cd data && sha256sum -c --quiet MANIFEST.sha256); then
  echo "all files match data/MANIFEST.sha256"
else
  echo "WARNING: some files differ from the ones the committed results used" >&2
fi
