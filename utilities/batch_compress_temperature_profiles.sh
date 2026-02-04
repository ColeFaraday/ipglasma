#!/bin/bash
# Usage: ./batch_compress_temperature_profiles.sh /path/to/parent_folder

PARENT_FOLDER="$1"
SCRIPT="$(dirname "$0")/compress_temperature_profiles_to_hdf5.py"
PATTERN="temperature_profile_eos9_condensed_t0.4-*.dat"

if [ -z "$PARENT_FOLDER" ]; then
  echo "Usage: $0 /path/to/parent_folder"
  exit 1
fi

for dir in "$PARENT_FOLDER"/*/; do
  [ -d "$dir" ] || continue
  BASENAME=$(basename "$dir")
  OUTPUT="$PARENT_FOLDER/${BASENAME}.h5"
  "$SCRIPT" --output "$OUTPUT" --pattern "$PATTERN" "$dir"
done
