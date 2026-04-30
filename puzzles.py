from __future__ import annotations

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
    """Up to 8 unique orientations (4 rotations x flip)."""
    result: set[frozenset[tuple[int, int]]] = set()
    cur = _normalize(frozenset(raw))
    for _ in range(4):
        result.add(cur)
        result.add(_reflect(cur))
        cur = _rotate90(cur)
    return result

# ---------------------------------------------------------------------------
# Puzzle definition
# ---------------------------------------------------------------------------

class Puzzle:
    def __init__(self,
                 name: str,
                 months: list[str],
                 rows: int,
                 cols: int,
                 board_dict: dict[tuple[int, int], str],
                 invalid: set[tuple[int, int]],
                 pieces_raw: list[set[tuple[int, int]]],
                 piece_colors: list[str] | None = None):
        self.name = name
        self.months = months
        self.rows = rows
        self.cols = cols
        self.board = board_dict
        self.invalid = invalid
        self.pieces_raw = pieces_raw
        
        self.num_pieces = len(self.pieces_raw)
        self.piece_sizes = [len(p) for p in self.pieces_raw]
        self.piece_colors = piece_colors or [
            "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
            "#9B59B6", "#1ABC9C", "#E67E22", "#2980B9",
            "#D35400", "#C0392B"
        ][:self.num_pieces]

        self.cell_to_idx: dict[tuple[int, int], int] = {
            cell: i for i, cell in enumerate(sorted(self.board))
        }
        self.idx_to_cell: dict[int, tuple[int, int]] = {v: k for k, v in self.cell_to_idx.items()}
        self.num_cells = len(self.board)

        self.all_placements: list[list[int]] = [
            self._compute_placements(raw) for raw in self.pieces_raw
        ]
        
        self.placements_by_cell: list[list[list[int]]] = [
            [
                [mask for mask in self.all_placements[p] if mask & (1 << bit)]
                for bit in range(self.num_cells)
            ]
            for p in range(self.num_pieces)
        ]

    def _compute_placements(self, raw: set[tuple[int, int]]) -> list[int]:
        seen: set[int] = set()
        masks: list[int] = []
        for orientation in all_orientations(raw):
            cells = list(orientation)
            for dr in range(self.rows):
                for dc in range(self.cols):
                    placed = tuple((r + dr, c + dc) for r, c in cells)
                    if all(pos in self.cell_to_idx for pos in placed):
                        mask = 0
                        for pos in placed:
                            mask |= 1 << self.cell_to_idx[pos]
                        if mask not in seen:
                            seen.add(mask)
                            masks.append(mask)
        return masks

# ---------------------------------------------------------------------------
# Standard Puzzle definition
# ---------------------------------------------------------------------------

_std_months = [
    'Jan', 'Fev', 'Mar', 'Abr',
    'Mai', 'Jun', 'Jul', 'Ago',
    'Set', 'Out', 'Nov', 'Dez',
]
_std_rows = 7
_std_cols = 8
_std_invalid = {(6, 7)}

def _build_std_board() -> dict[tuple[int, int], str]:
    board: dict[tuple[int, int], str] = {}
    for row in range(3):
        for col in range(_std_cols):
            month_idx = row * 4 + col // 2
            board[(row, col)] = _std_months[month_idx]
    day = 1
    for row in range(3, _std_rows):
        for col in range(_std_cols):
            if (row, col) in _std_invalid:
                continue
            board[(row, col)] = str(day)
            day += 1
    return board

_std_pieces = [
    {(0,0),(0,1),(0,2),(0,3),(1,1),(1,2)},
    {(0,0),(0,1),(0,2),(1,0),(1,1),(1,2),(2,2)},
    {(0,0),(0,1),(0,2),(0,3),(1,0),(1,1),(1,2)},
    {(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)},
    {(0,0),(1,0),(2,0),(3,0),(4,0),(4,1),(4,2)},
    {(0,0),(1,0),(2,0),(3,0),(3,1),(3,2),(3,3)},
    {(0,0),(1,0),(1,1),(1,2),(2,0),(2,1)},
    {(0,0),(0,1),(0,2),(0,3),(1,0),(1,1)},
]

StandardPuzzle = Puzzle(
    name="Padrão",
    months=_std_months,
    rows=_std_rows,
    cols=_std_cols,
    board_dict=_build_std_board(),
    invalid=_std_invalid,
    pieces_raw=_std_pieces
)

# ---------------------------------------------------------------------------
# Green Puzzle definition
# ---------------------------------------------------------------------------

_grn_months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]
_grn_rows = 7
_grn_cols = 7
_grn_invalid = {(0, 6), (1, 6), (6, 3), (6, 4), (6, 5), (6, 6)}

def _build_grn_board() -> dict[tuple[int, int], str]:
    board: dict[tuple[int, int], str] = {}
    for col in range(6):
        board[(0, col)] = _grn_months[col]
        board[(1, col)] = _grn_months[col + 6]
    day = 1
    for row in range(2, _grn_rows):
        for col in range(_grn_cols):
            if (row, col) in _grn_invalid:
                continue
            board[(row, col)] = str(day)
            day += 1
    return board

_grn_pieces = [
    {(0,0), (1,0), (2,0), (3,0), (3,1)},
    {(0,0), (0,1), (1,0), (1,1), (2,0), (2,1)},
    {(0,0), (1,0), (2,0), (2,1), (3,0)},
    {(0,0), (0,1), (1,1), (2,0), (2,1)},
    {(0,1), (1,0), (1,1), (2,0), (3,0)},
    {(0,0), (1,0), (1,1), (2,0), (2,1)},
    {(0,0), (1,0), (2,0), (2,1), (2,2)},
    {(0,1), (0,2), (1,1), (2,0), (2,1)},
]

GreenPuzzle = Puzzle(
    name="Verde",
    months=_grn_months,
    rows=_grn_rows,
    cols=_grn_cols,
    board_dict=_build_grn_board(),
    invalid=_grn_invalid,
    pieces_raw=_grn_pieces,
    piece_colors=["#1ABC9C", "#16A085", "#2ECC71", "#27AE60", 
                  "#00FF7F", "#3CB371", "#2E8B57", "#006400"]
)

PUZZLES = [StandardPuzzle, GreenPuzzle]
