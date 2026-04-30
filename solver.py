from __future__ import annotations
import sys
import time
import argparse
from multiprocessing import Pool
from board import BOARD, CELL_TO_IDX, IDX_TO_CELL, MONTHS, NUM_CELLS, ROWS, COLS, INVALID
from pieces import ALL_PLACEMENTS, PLACEMENTS_BY_CELL, NUM_PIECES, PIECE_SIZES


FULL_MASK = (1 << NUM_CELLS) - 1
PIECE_CHARS = "ABCDEFGH"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(month: str, day: int, workers: int = 1) -> list[tuple[int, int]] | None:
    """
    Return a list of (piece_index, placement_mask) that solves the puzzle,
    leaving the given month and day exposed. Returns None if unsolvable.

    workers: number of parallel processes (default 1 = single-threaded).
    """
    available = _prepare(month, day)
    remaining = list(range(NUM_PIECES))

    if workers == 1:
        return _backtrack(available, remaining, [])

    return _parallel_first(available, remaining, workers)


def solve_with_fixed(
    month: str,
    day: int,
    fixed: list[tuple[int, int]],
    workers: int = 1,
) -> list[tuple[int, int]] | None:
    """
    Solve with some pieces already placed.
    fixed: list of (piece_index, placement_mask) pre-placed by the user.
    Returns the full solution (fixed + solver-placed), or None if unsolvable.
    """
    available = _prepare(month, day)
    fixed_pieces: set[int] = set()
    for piece_idx, mask in fixed:
        available &= ~mask   # those cells are already covered
        fixed_pieces.add(piece_idx)

    remaining = [p for p in range(NUM_PIECES) if p not in fixed_pieces]

    if workers == 1:
        return _backtrack(available, remaining, list(fixed))
    return _parallel_first(available, remaining, workers)


def solve_all(month: str, day: int, workers: int = 1) -> list[list[tuple[int, int]]]:
    """
    Return all solutions for the given month and day.

    workers: number of parallel processes (default 1 = single-threaded).
    """
    available = _prepare(month, day)
    remaining = list(range(NUM_PIECES))

    if workers == 1:
        results: list[list[tuple[int, int]]] = []
        _backtrack_all(available, remaining, [], results)
        return results

    return _parallel_all(available, remaining, workers)


# ---------------------------------------------------------------------------
# Input validation / board setup
# ---------------------------------------------------------------------------

def _prepare(month: str, day: int) -> int:
    if month not in MONTHS:
        raise ValueError(f"Invalid month '{month}'. Choose from: {MONTHS}")
    if not (1 <= day <= 31):
        raise ValueError(f"Day must be 1–31, got {day}")

    month_pos = [pos for pos, lbl in BOARD.items() if lbl == month]
    day_pos   = [pos for pos, lbl in BOARD.items() if lbl == str(day)]

    if not day_pos:
        raise ValueError(f"Day {day} not found on board.")

    exposed = 0
    for pos in month_pos + day_pos:
        exposed |= 1 << CELL_TO_IDX[pos]

    return FULL_MASK & ~exposed


# ---------------------------------------------------------------------------
# Single-threaded backtracking
# ---------------------------------------------------------------------------

def _backtrack(
    available: int,
    remaining: list[int],
    placed: list[tuple[int, int]],
) -> list[tuple[int, int]] | None:
    if not remaining:
        return placed if available == 0 else None

    target_bit = (available & -available).bit_length() - 1

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in PLACEMENTS_BY_CELL[piece_idx][target_bit]:
            if (mask & available) == mask:
                result = _backtrack(available ^ mask, rest, placed + [(piece_idx, mask)])
                if result is not None:
                    return result

    return None


def _backtrack_all(
    available: int,
    remaining: list[int],
    placed: list[tuple[int, int]],
    results: list,
) -> None:
    if not remaining:
        if available == 0:
            results.append(list(placed))
        return

    target_bit = (available & -available).bit_length() - 1

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in PLACEMENTS_BY_CELL[piece_idx][target_bit]:
            if (mask & available) == mask:
                placed.append((piece_idx, mask))
                _backtrack_all(available ^ mask, rest, placed, results)
                placed.pop()


# ---------------------------------------------------------------------------
# Parallel helpers — must be module-level to be picklable on Windows
# ---------------------------------------------------------------------------

def _top_level_tasks(available: int, remaining: list[int]) -> list[tuple]:
    """Split the root of the search tree into independent sub-problems."""
    target_bit = (available & -available).bit_length() - 1
    tasks = []
    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in PLACEMENTS_BY_CELL[piece_idx][target_bit]:
            if (mask & available) == mask:
                tasks.append((available ^ mask, rest, [(piece_idx, mask)]))
    return tasks


def _worker_first(args: tuple) -> list[tuple[int, int]] | None:
    available, remaining, placed = args
    return _backtrack(available, remaining, placed)


def _worker_all(args: tuple) -> list[list[tuple[int, int]]]:
    available, remaining, placed = args
    results: list = []
    _backtrack_all(available, remaining, placed, results)
    return results


def _parallel_first(
    available: int, remaining: list[int], workers: int
) -> list[tuple[int, int]] | None:
    tasks = _top_level_tasks(available, remaining)
    with Pool(workers) as pool:
        for result in pool.imap_unordered(_worker_first, tasks, chunksize=4):
            if result is not None:
                pool.terminate()
                return result
    return None


def _parallel_all(
    available: int, remaining: list[int], workers: int
) -> list[list[tuple[int, int]]]:
    tasks = _top_level_tasks(available, remaining)
    with Pool(workers) as pool:
        groups = pool.map(_worker_all, tasks, chunksize=2)
    return [sol for group in groups for sol in group]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_solution(solution: list[tuple[int, int]], month: str, day: int) -> None:
    cell_char: dict[tuple[int, int], str] = {}
    for piece_idx, mask in solution:
        char = PIECE_CHARS[piece_idx]
        for bit in range(NUM_CELLS):
            if mask & (1 << bit):
                cell_char[IDX_TO_CELL[bit]] = char

    exposed_cells = {pos for pos, lbl in BOARD.items()
                     if lbl == month or lbl == str(day)}

    GREEN = "\033[1;32m"
    RESET = "\033[0m"

    print(f"\nSolution for {month} {day}:\n")
    print("     " + "  ".join(f"C{c}" for c in range(COLS)))
    print("     " + "-" * (COLS * 5 - 1))
    for r in range(ROWS):
        parts = []
        for c in range(COLS):
            if (r, c) in INVALID:
                parts.append("  -- ")
            elif (r, c) in exposed_cells:
                parts.append(f"{GREEN}{BOARD[(r,c)]:>4} {RESET}")
            else:
                parts.append(f"{cell_char.get((r,c), '?'):>4} ")
        print(f"R{r} | {''.join(parts)}")

    print("\nLegend:")
    for piece_idx, _ in sorted(solution, key=lambda x: x[0]):
        print(f"  {PIECE_CHARS[piece_idx]} = P{piece_idx}  ({PIECE_SIZES[piece_idx]} cells)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calendar Puzzle Solver")
    parser.add_argument("month", help=f"Month ({', '.join(MONTHS)})")
    parser.add_argument("day",   type=int, help="Day number (1–31)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel processes (default: 1)")
    args = parser.parse_args()

    print(f"Solving {args.month} {args.day} with {args.workers} worker(s)...")
    t0 = time.perf_counter()
    solution = solve(args.month, args.day, workers=args.workers)
    elapsed = time.perf_counter() - t0

    if solution is None:
        print("No solution found.")
        sys.exit(1)

    print_solution(solution, args.month, args.day)
    print(f"\nSolved in {elapsed:.3f}s")
