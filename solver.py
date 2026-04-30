from __future__ import annotations
import sys
import time
import argparse
from multiprocessing import Pool
from puzzles import PUZZLES, Puzzle

PIECE_CHARS = "ABCDEFGH"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(puzzle: Puzzle, month: str, day: int, workers: int = 1) -> list[tuple[int, int]] | None:
    """
    Return a list of (piece_index, placement_mask) that solves the puzzle,
    leaving the given month and day exposed. Returns None if unsolvable.

    workers: number of parallel processes (default 1 = single-threaded).
    """
    available = _prepare(puzzle, month, day)
    remaining = list(range(puzzle.num_pieces))

    if workers == 1:
        return _backtrack(puzzle, available, remaining, [])

    return _parallel_first(puzzle, available, remaining, workers)


def solve_with_fixed(
    puzzle: Puzzle,
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
    available = _prepare(puzzle, month, day)
    fixed_pieces: set[int] = set()
    for piece_idx, mask in fixed:
        available &= ~mask   # those cells are already covered
        fixed_pieces.add(piece_idx)

    remaining = [p for p in range(puzzle.num_pieces) if p not in fixed_pieces]

    if workers == 1:
        return _backtrack(puzzle, available, remaining, list(fixed))
    return _parallel_first(puzzle, available, remaining, workers)


def solve_all(puzzle: Puzzle, month: str, day: int, workers: int = 1) -> list[list[tuple[int, int]]]:
    """
    Return all solutions for the given month and day.

    workers: number of parallel processes (default 1 = single-threaded).
    """
    available = _prepare(puzzle, month, day)
    remaining = list(range(puzzle.num_pieces))

    if workers == 1:
        results: list[list[tuple[int, int]]] = []
        _backtrack_all(puzzle, available, remaining, [], results)
        return results

    return _parallel_all(puzzle, available, remaining, workers)


# ---------------------------------------------------------------------------
# Input validation / board setup
# ---------------------------------------------------------------------------

def _prepare(puzzle: Puzzle, month: str, day: int) -> int:
    if month not in puzzle.months:
        raise ValueError(f"Invalid month '{month}'. Choose from: {puzzle.months}")
    if not (1 <= day <= 31):
        raise ValueError(f"Day must be 1–31, got {day}")

    month_pos = [pos for pos, lbl in puzzle.board.items() if lbl == month]
    day_pos   = [pos for pos, lbl in puzzle.board.items() if lbl == str(day)]

    if not day_pos:
        raise ValueError(f"Day {day} not found on board.")

    exposed = 0
    for pos in month_pos + day_pos:
        exposed |= 1 << puzzle.cell_to_idx[pos]

    full_mask = (1 << puzzle.num_cells) - 1
    return full_mask & ~exposed


# ---------------------------------------------------------------------------
# Single-threaded backtracking
# ---------------------------------------------------------------------------

def _backtrack(
    puzzle: Puzzle,
    available: int,
    remaining: list[int],
    placed: list[tuple[int, int]],
) -> list[tuple[int, int]] | None:
    if not remaining:
        return placed if available == 0 else None

    target_bit = (available & -available).bit_length() - 1

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in puzzle.placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                result = _backtrack(puzzle, available ^ mask, rest, placed + [(piece_idx, mask)])
                if result is not None:
                    return result

    return None


def _backtrack_all(
    puzzle: Puzzle,
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
        for mask in puzzle.placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                placed.append((piece_idx, mask))
                _backtrack_all(puzzle, available ^ mask, rest, placed, results)
                placed.pop()


# ---------------------------------------------------------------------------
# Parallel helpers — must be module-level to be picklable on Windows
# ---------------------------------------------------------------------------
# Because 'puzzle' is passed around and multiprocessing requires pickling, 
# we pass puzzle index to workers to avoid pickling large objects if we can,
# or we just pass the puzzle directly. Python can pickle custom objects.

def _top_level_tasks(puzzle: Puzzle, available: int, remaining: list[int]) -> list[tuple]:
    """Split the root of the search tree into independent sub-problems."""
    target_bit = (available & -available).bit_length() - 1
    tasks = []
    # To make pickling smaller, we could just pass puzzle index in PUZZLES
    puzzle_idx = PUZZLES.index(puzzle)

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in puzzle.placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                tasks.append((puzzle_idx, available ^ mask, rest, [(piece_idx, mask)]))
    return tasks


def _worker_first(args: tuple) -> list[tuple[int, int]] | None:
    puzzle_idx, available, remaining, placed = args
    puzzle = PUZZLES[puzzle_idx]
    return _backtrack(puzzle, available, remaining, placed)


def _worker_all(args: tuple) -> list[list[tuple[int, int]]]:
    puzzle_idx, available, remaining, placed = args
    puzzle = PUZZLES[puzzle_idx]
    results: list = []
    _backtrack_all(puzzle, available, remaining, placed, results)
    return results


def _parallel_first(
    puzzle: Puzzle, available: int, remaining: list[int], workers: int
) -> list[tuple[int, int]] | None:
    tasks = _top_level_tasks(puzzle, available, remaining)
    with Pool(workers) as pool:
        for result in pool.imap_unordered(_worker_first, tasks, chunksize=4):
            if result is not None:
                pool.terminate()
                return result
    return None


def _parallel_all(
    puzzle: Puzzle, available: int, remaining: list[int], workers: int
) -> list[list[tuple[int, int]]]:
    tasks = _top_level_tasks(puzzle, available, remaining)
    with Pool(workers) as pool:
        groups = pool.map(_worker_all, tasks, chunksize=2)
    return [sol for group in groups for sol in group]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_solution(puzzle: Puzzle, solution: list[tuple[int, int]], month: str, day: int) -> None:
    cell_char: dict[tuple[int, int], str] = {}
    for piece_idx, mask in solution:
        char = PIECE_CHARS[piece_idx]
        for bit in range(puzzle.num_cells):
            if mask & (1 << bit):
                cell_char[puzzle.idx_to_cell[bit]] = char

    exposed_cells = {pos for pos, lbl in puzzle.board.items()
                     if lbl == month or lbl == str(day)}

    GREEN = "\033[1;32m"
    RESET = "\033[0m"

    print(f"\nSolution for {month} {day} ({puzzle.name}):\n")
    print("     " + "  ".join(f"C{c}" for c in range(puzzle.cols)))
    print("     " + "-" * (puzzle.cols * 5 - 1))
    for r in range(puzzle.rows):
        parts = []
        for c in range(puzzle.cols):
            if (r, c) in puzzle.invalid:
                parts.append("  -- ")
            elif (r, c) in exposed_cells:
                parts.append(f"{GREEN}{puzzle.board[(r,c)]:>4} {RESET}")
            else:
                parts.append(f"{cell_char.get((r,c), '?'):>4} ")
        print(f"R{r} | {''.join(parts)}")

    print("\nLegend:")
    for piece_idx, _ in sorted(solution, key=lambda x: x[0]):
        print(f"  {PIECE_CHARS[piece_idx]} = P{piece_idx}  ({puzzle.piece_sizes[piece_idx]} cells)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calendar Puzzle Solver")
    parser.add_argument("month", help=f"Month label")
    parser.add_argument("day",   type=int, help="Day number (1–31)")
    parser.add_argument("--puzzle", type=int, default=0,
                        help="Puzzle index (0=Standard, 1=Green)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel processes (default: 1)")
    args = parser.parse_args()

    puzzle = PUZZLES[args.puzzle]

    print(f"Solving {args.month} {args.day} on {puzzle.name} puzzle with {args.workers} worker(s)...")
    t0 = time.perf_counter()
    solution = solve(puzzle, args.month, args.day, workers=args.workers)
    elapsed = time.perf_counter() - t0

    if solution is None:
        print("No solution found.")
        sys.exit(1)

    print_solution(puzzle, solution, args.month, args.day)
    print(f"\nSolved in {elapsed:.3f}s")
