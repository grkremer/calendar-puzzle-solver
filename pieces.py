# Compatibility shim — re-exports PUZZLE_CLASSIC data under the original names.
# New code should import directly from puzzles.py and use PuzzleSet attributes.
from puzzles import PUZZLE_CLASSIC as _p
from puzzle_set import all_orientations  # noqa: F401 — re-exported for callers

PIECES_RAW       = _p.pieces_raw
ALL_PLACEMENTS   = _p.all_placements
PLACEMENTS_BY_CELL = _p.placements_by_cell
NUM_PIECES       = _p.num_pieces
PIECE_SIZES      = _p.piece_sizes
