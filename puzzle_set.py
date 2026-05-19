from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Orientation helpers (pure functions, no board dependency)
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
# Placement pre-computation
# ---------------------------------------------------------------------------

def _compute_placements(
    raw: set[tuple[int, int]],
    rows: int,
    cols: int,
    cell_to_idx: dict[tuple[int, int], int],
) -> list[int]:
    seen: set[int] = set()
    masks: list[int] = []
    for orientation in all_orientations(raw):
        cells = list(orientation)
        for dr in range(rows):
            for dc in range(cols):
                placed = tuple((r + dr, c + dc) for r, c in cells)
                if all(pos in cell_to_idx for pos in placed):
                    mask = 0
                    for pos in placed:
                        mask |= 1 << cell_to_idx[pos]
                    if mask not in seen:
                        seen.add(mask)
                        masks.append(mask)
    return masks


# ---------------------------------------------------------------------------
# PuzzleSet — board + pieces + pre-computed data, all in one place
# ---------------------------------------------------------------------------

@dataclass
class PuzzleSet:
    name: str
    rows: int
    cols: int
    invalid: set[tuple[int, int]]
    board: dict[tuple[int, int], str]
    months: list[str]
    cell_to_idx: dict[tuple[int, int], int]
    idx_to_cell: dict[int, tuple[int, int]]
    num_cells: int
    pieces_raw: list[set[tuple[int, int]]]
    piece_sizes: list[int]
    all_placements: list[list[int]]
    placements_by_cell: list[list[list[int]]]
    piece_colors: list[str]

    @property
    def num_pieces(self) -> int:
        return len(self.pieces_raw)

    @classmethod
    def create(
        cls,
        name: str,
        rows: int,
        cols: int,
        invalid: set[tuple[int, int]],
        months: list[str],
        board: dict[tuple[int, int], str],
        pieces_raw: list[set[tuple[int, int]]],
        piece_colors: list[str] | None = None,
    ) -> 'PuzzleSet':
        cell_to_idx = {cell: i for i, cell in enumerate(sorted(board))}
        idx_to_cell = {v: k for k, v in cell_to_idx.items()}
        num_cells = len(board)

        all_placements = [
            _compute_placements(raw, rows, cols, cell_to_idx)
            for raw in pieces_raw
        ]
        placements_by_cell = [
            [
                [mask for mask in all_placements[p] if mask & (1 << bit)]
                for bit in range(num_cells)
            ]
            for p in range(len(pieces_raw))
        ]

        if piece_colors is None:
            defaults = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12',
                        '#9B59B6', '#1ABC9C', '#E67E22', '#2980B9']
            piece_colors = defaults[:len(pieces_raw)]

        return cls(
            name=name, rows=rows, cols=cols, invalid=invalid,
            board=board, months=months,
            cell_to_idx=cell_to_idx, idx_to_cell=idx_to_cell,
            num_cells=num_cells, pieces_raw=pieces_raw,
            piece_sizes=[len(p) for p in pieces_raw],
            all_placements=all_placements,
            placements_by_cell=placements_by_cell,
            piece_colors=piece_colors,
        )
