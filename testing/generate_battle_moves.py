#!/usr/bin/env python3
"""
Generate a new `battle_moves.h` in `testing/` that includes a `.category` field
for moves coming from `testing/moves.csv` (generation_id <= 3).

Usage: run from repo root:
    python3 testing/generate_battle_moves.py

This script:
- Reads `testing/moves.csv` (expects header row).
- Reads `src/data/battle_moves.h` and extracts move blocks.
- For each move block, maps the move constant (e.g. MOVE_POUND) to the CSV
  identifier (e.g. "pound") and looks up `generation_id` and `damage_class_id`.
- If the move's `generation_id` <= 3, writes the move block to
  `testing/battle_moves.h` with an extra line `    .category = <n>,` inserted
  before the closing brace of the block. The category value is the
  `damage_class_id` (1=status, 2=attack, 3=spec_attack) per the user's mapping.

Note: the script preserves most original formatting and only includes moves
that are present in the CSV and have generation_id <= 3.
"""

import csv
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV_PATH = os.path.join(REPO_ROOT, 'testing', 'moves.csv')
SRC_BATTLE_MOVES = os.path.join(REPO_ROOT, 'src', 'data', 'battle_moves.h')
OUT_PATH = os.path.join(REPO_ROOT, 'testing', 'battle_moves.h')


def load_moves_csv(path):
    moves = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            identifier = r['identifier']
            try:
                gen = int(r['generation_id'])
            except Exception:
                gen = None
            # damage_class_id may be empty; try to parse
            try:
                dmg = int(r['damage_class_id'])
            except Exception:
                dmg = None
            moves[identifier] = {'generation_id': gen, 'damage_class_id': dmg}
    return moves


def move_constant_to_identifier(move_const):
    # MOVE_KARATE_CHOP -> karate-chop
    name = move_const[len('MOVE_'):]
    name = name.lower()
    name = name.replace('_', '-')
    return name


def generate_with_category(src_path, csv_moves, out_path):
    start_array_re = re.compile(r"^const struct BattleMove gBattleMoves\[MOVES_COUNT\] =")
    move_entry_re = re.compile(r"^\s*\[(MOVE_[A-Z0-9_]+)\] =\s*$")

    with open(src_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    out_lines = []
    i = 0
    n = len(lines)

    # Copy leading content up to the array start
    while i < n:
        out_lines.append(lines[i])
        if start_array_re.search(lines[i]):
            i += 1
            break
        i += 1

    # After the declaration line, there should be the opening brace line(s)
    # Copy until we hit the first move entry or the closing brace
    while i < n:
        m = move_entry_re.match(lines[i])
        if m:
            break
        out_lines.append(lines[i])
        # stop if reached closing of array
        if lines[i].strip() == '};':
            i += 1
            break
        i += 1

    # Process each move entry block
    while i < n:
        m = move_entry_re.match(lines[i])
        if not m:
            # copy remainder (closing brace etc.) and finish
            out_lines.append(lines[i])
            i += 1
            continue

        move_const = m.group(1)
        identifier = move_constant_to_identifier(move_const)
        # capture the whole block until the line that is just '    },' or '\t},'
        block_lines = [lines[i]]
        i += 1
        # consume until we find a line that has only closing brace and a comma
        while i < n:
            block_lines.append(lines[i])
            if re.match(r"^\s*},\s*$", lines[i]):
                i += 1
                break
            i += 1

        # decide whether to include the block
        csv_entry = csv_moves.get(identifier)
        if csv_entry and csv_entry['generation_id'] is not None and csv_entry['generation_id'] <= 3:
            # determine category value
            cat = csv_entry['damage_class_id']
            if cat is None:
                cat = 1
            # insert category line before the final closing '},' in block_lines
            # find index of the last line (the closing '},') and insert before it
            for idx in range(len(block_lines)-1, -1, -1):
                if re.match(r"^\s*},\s*$", block_lines[idx]):
                    indent = re.match(r"^(\s*)", block_lines[idx-1]).group(1) if idx-1 >= 0 else '    '
                    # use the indent of the previous field line
                    cat_line = indent + '.category = %d,\n' % (cat)
                    # insert before idx
                    block_lines.insert(idx, cat_line)
                    break
            out_lines.extend(block_lines)
        else:
            # skip the block (do not write it to output)
            # For transparency, add a comment indicating skip
            out_lines.append('    /* Skipped %s (not in moves.csv gen<=3) */\n' % move_const)

    # Write output
    with open(out_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    print('Wrote', out_path)


def main():
    if not os.path.exists(CSV_PATH):
        print('moves.csv not found at', CSV_PATH, file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(SRC_BATTLE_MOVES):
        print('source battle_moves.h not found at', SRC_BATTLE_MOVES, file=sys.stderr)
        sys.exit(1)

    csv_moves = load_moves_csv(CSV_PATH)
    generate_with_category(SRC_BATTLE_MOVES, csv_moves, OUT_PATH)


if __name__ == '__main__':
    main()
