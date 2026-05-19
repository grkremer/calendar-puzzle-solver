# Compatibility shim — re-exports PUZZLE_CLASSIC data under the original names.
# New code should import directly from puzzles.py and use PuzzleSet attributes.
from puzzles import PUZZLE_CLASSIC as _p

MONTHS    = _p.months
ROWS      = _p.rows
COLS      = _p.cols
INVALID   = _p.invalid
BOARD     = _p.board
CELL_TO_IDX = _p.cell_to_idx
IDX_TO_CELL = _p.idx_to_cell
NUM_CELLS = _p.num_cells


def build_board() -> dict:
    return BOARD


def print_board(highlight: set | None = None) -> None:
    highlight = highlight or set()
    print("     " + "  ".join(f"C{c}" for c in range(COLS)))
    print("     " + "-" * (COLS * 5 - 1))
    for r in range(ROWS):
        parts = []
        for c in range(COLS):
            if (r, c) in INVALID:
                parts.append("  -- ")
            elif (r, c) in highlight:
                label = BOARD[(r, c)]
                parts.append(f"\033[1;32m{label:>4}\033[0m ")
            else:
                label = BOARD.get((r, c), "")
                parts.append(f"{label:>4} ")
        print(f"R{r} | {''.join(parts)}")
