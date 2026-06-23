#!/usr/bin/env bash

# Usage:
#   ./normalize_csv.sh file1.csv file2.csv ...
#
# Output:
#   file1-NORMALIZED.csv
#   file2-NORMALIZED.csv

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 file1.csv file2.csv ..."
    exit 1
fi

for in in "$@"; do
    [ ! -f "$in" ] && echo "Skipping missing file: $in" && continue

    out="normalized.${in%.csv}.csv"

    awk -F',' '
    BEGIN {
        header_seen = 0
    }

    FNR<=5 {
        next
    }

    FNR==6 {
        if ($1 ~ /[a-zA-Z]/) {
            header_seen = 1
            next
        }
    }

    {
        if (FNR == (header_seen ? 6 : 7)) {
            base = $1
        }

        t = $1 - base
        v = $2

        print t "," v
    }
    ' "$in" > "$out"

    echo "Wrote: $out"
done
