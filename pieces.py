from __future__ import annotations
from board import BOARD, CELL_TO_IDX, ROWS, COLS, NUM_CELLS


# ---------------------------------------------------------------------------
# Orientation helpers
# ---------------------------------------------------------------------------

def _normalize(cells: frozenset[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return frozenset((r - min_r, c - min_c) for r, c in cells)

def _rotate90(cells: frozenset[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    return _normalize(frozenset((c, -r) for r, c in cells))

def _reflect(cells: frozenset[tuple[int, int]]) -> frozenset[tuple[int, int]]:
    return _normalize(frozenset((r, -c) for r, c in cells))

def all_orientations(raw: set[tuple[int, int]]) -> set[frozenset[tuple[int, int]]]:
    """Up to 8 unique orientations (4 rotations × flip)."""
    result: set[frozenset[tuple[int, int]]] = set()
    cur = _normalize(frozenset(raw))
    for _ in range(4):
        result.add(cur)
        result.add(_reflect(cur))
        cur = _rotate90(cur)
    return result


# ---------------------------------------------------------------------------
# Piece shapes
# ---------------------------------------------------------------------------

PIECES_RAW: list[set[tuple[int, int]]] = [
    # P0 (6): oooo
    #          oo
    {(0,0),(0,1),(0,2),(0,3),(1,1),(1,2)},

    # P1 (7): ooo
    #         ooo
    #           o
    {(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,2)},

    # P2 (7): oooo
    #         ooo
    {(0,0),(0,1),(0,2),(0,3),(1,0),(1,1),(1,2)},

    # P3 (6): ooo
    #         ooo
    {(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)},

    # P4 (7): o
    #         o
    #         o
    #         o
    #         ooo
    {(0,0),(1,0),(2,0),(3,0),(4,0),(4,1),(4,2)},

    # P5 (7): o
    #         o
    #         o
    #         oooo
    {(0,0),(1,0),(2,0),(3,0),(3,1),(3,2),(3,3)},

    # P6 (6): o
    #         ooo
    #         oo
    {(0,0),(1,0),(1,1),(1,2),(2,0),(2,1)},

    # P7 (6): oooo
    #         oo
    {(0,0),(0,1),(0,2),(0,3),(1,0),(1,1)},
]

NUM_PIECES = len(PIECES_RAW)
PIECE_SIZES = [len(p) for p in PIECES_RAW]
assert sum(PIECE_SIZES) == 52, f"Expected 52 cells total, got {sum(PIECE_SIZES)}"


# ---------------------------------------------------------------------------
# Pre-compute all valid placements as bitmasks
# ---------------------------------------------------------------------------

def _compute_placements(raw: set[tuple[int, int]]) -> list[int]:
    seen: set[int] = set()
    masks: list[int] = []
    for orientation in all_orientations(raw):
        cells = list(orientation)
        for dr in range(ROWS):
            for dc in range(COLS):
                placed = tuple((r + dr, c + dc) for r, c in cells)
                if all(pos in CELL_TO_IDX for pos in placed):
                    mask = 0
                    for pos in placed:
                        mask |= 1 << CELL_TO_IDX[pos]
                    if mask not in seen:
                        seen.add(mask)
                        masks.append(mask)
    return masks


# ALL_PLACEMENTS[p] = list of bitmasks for every valid placement of piece p
ALL_PLACEMENTS: list[list[int]] = [_compute_placements(raw) for raw in PIECES_RAW]

# PLACEMENTS_BY_CELL[p][bit] = placements of piece p that include cell `bit`
# Used by the solver to quickly find candidates when filling a specific cell.
PLACEMENTS_BY_CELL: list[list[list[int]]] = [
    [
        [mask for mask in ALL_PLACEMENTS[p] if mask & (1 << bit)]
        for bit in range(NUM_CELLS)
    ]
    for p in range(NUM_PIECES)
]


if __name__ == "__main__":
    for i, masks in enumerate(ALL_PLACEMENTS):
        print(f"P{i} ({PIECE_SIZES[i]} cells): {len(masks)} valid placements")
