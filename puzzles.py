from puzzle_set import PuzzleSet

_MONTHS_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
_MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

_CLASSIC_INVALID: set[tuple[int, int]] = {(6, 7)}
_B_INVALID: set[tuple[int, int]] = {(0, 6), (1, 6), (6, 3), (6, 4), (6, 5), (6, 6)}


def _build_classic_board() -> dict[tuple[int, int], str]:
    """7×8 board: rows 0-2 = months (each label spans 2 cols), rows 3-6 = days 1-31."""
    board: dict[tuple[int, int], str] = {}
    for row in range(3):
        for col in range(8):
            board[(row, col)] = _MONTHS_PT[row * 4 + col // 2]
    day = 1
    for row in range(3, 7):
        for col in range(8):
            if (row, col) in _CLASSIC_INVALID:
                continue
            board[(row, col)] = str(day)
            day += 1
    return board


def _build_b_board() -> dict[tuple[int, int], str]:
    """7×7 board: rows 0-1 = months (1 cell each), rows 2-6 = days 1-31."""
    board: dict[tuple[int, int], str] = {}
    for col in range(6):
        board[(0, col)] = _MONTHS_EN[col]
        board[(1, col)] = _MONTHS_EN[col + 6]
    day = 1
    for row in range(2, 7):
        for col in range(7):
            if (row, col) in _B_INVALID:
                continue
            board[(row, col)] = str(day)
            day += 1
    return board


# ---------------------------------------------------------------------------
# Piece shapes
# ---------------------------------------------------------------------------

_CLASSIC_PIECES: list[set[tuple[int, int]]] = [
    # P0 (6): oooo / _oo
    {(0, 0), (0, 1), (0, 2), (0, 3), (1, 1), (1, 2)},
    # P1 (7): ooo / ooo / __o
    {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 2)},
    # P2 (7): oooo / ooo
    {(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2)},
    # P3 (6): ooo / ooo
    {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)},
    # P4 (7): o/o/o/o/ooo
    {(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2)},
    # P5 (7): o/o/o/oooo
    {(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2), (3, 3)},
    # P6 (6): o/ooo/oo
    {(0, 0), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1)},
    # P7 (6): oooo/oo
    {(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1)},
]

_B_PIECES: list[set[tuple[int, int]]] = [
    # P0 (5): o/o/o/oo
    {(0, 0), (1, 0), (2, 0), (3, 0), (3, 1)},
    # P1 (6): oo/oo/oo
    {(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)},
    # P2 (5): o/o/oo/o
    {(0, 0), (1, 0), (2, 0), (2, 1), (3, 0)},
    # P3 (5): oo/_o/oo
    {(0, 0), (0, 1), (1, 1), (2, 0), (2, 1)},
    # P4 (5): _o/oo/o/o
    {(0, 1), (1, 0), (1, 1), (2, 0), (3, 0)},
    # P5 (5): o_/oo/oo
    {(0, 0), (1, 0), (1, 1), (2, 0), (2, 1)},
    # P6 (5): o/o/ooo
    {(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)},
    # P7 (5): _oo/o_/oo
    {(0, 1), (0, 2), (1, 0), (2, 0), (2, 1)},
]

assert sum(len(p) for p in _CLASSIC_PIECES) == 52
assert sum(len(p) for p in _B_PIECES) == 41


# ---------------------------------------------------------------------------
# Public puzzle instances
# ---------------------------------------------------------------------------

PUZZLE_CLASSIC = PuzzleSet.create(
    name='classic',
    rows=7, cols=8,
    invalid=_CLASSIC_INVALID,
    months=_MONTHS_PT,
    board=_build_classic_board(),
    pieces_raw=_CLASSIC_PIECES,
    piece_colors=[
        '#E74C3C', '#3498DB', '#2ECC71', '#F39C12',
        '#9B59B6', '#1ABC9C', '#E67E22', '#2980B9',
    ],
)

PUZZLE_B = PuzzleSet.create(
    name='puzzle_b',
    rows=7, cols=7,
    invalid=_B_INVALID,
    months=_MONTHS_EN,
    board=_build_b_board(),
    pieces_raw=_B_PIECES,
    piece_colors=[
        '#145A32', '#1E8449', '#27AE60', '#2ECC71',
        '#58D68D', '#82E0AA', '#196F3D', '#A9DFBF',
    ],
)
