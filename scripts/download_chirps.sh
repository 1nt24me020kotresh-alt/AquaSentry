#!/bin/bash
set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { log "ERROR: $*" >&2; }

BASE_URL="https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/netcdf"
OUTPUT_DIR="data/raw/chirps"
TOTAL=0
SKIPPED=0
FAILED=0

log "Starting CHIRPS download: 2015–2024 (120 files)"

for year in {2015..2024}; do
  for month in $(seq -w 1 12); do
    FILENAME="chirps-v2.0.${year}.${month}.days_p05.nc"
    OUTPUT_PATH="${OUTPUT_DIR}/${FILENAME}"

    if [ -f "$OUTPUT_PATH" ] && [ -s "$OUTPUT_PATH" ]; then
      log "SKIP (exists): ${FILENAME}"
      ((SKIPPED++)) || true
      continue
    fi

    log "Downloading: ${FILENAME}"
    if curl -fsSL --retry 3 --connect-timeout 60 \
        "${BASE_URL}/${FILENAME}" \
        -o "${OUTPUT_PATH}"; then
      log "  OK: ${FILENAME}"
      ((TOTAL++)) || true
    else
      error "  FAILED: ${FILENAME}"
      rm -f "${OUTPUT_PATH}"
      ((FAILED++)) || true
    fi
  done
done

log "Download complete. New: ${TOTAL}, Skipped: ${SKIPPED}, Failed: ${FAILED}"
TOTAL_FILES=$(ls data/raw/chirps/*.nc 2>/dev/null | wc -l)
log "Total CHIRPS files on disk: ${TOTAL_FILES}/120"
