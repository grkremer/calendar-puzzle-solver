from __future__ import annotations
import sys
import time
import argparse
from multiprocessing import Pool
from puzzle_set import PuzzleSet


PIECE_CHARS = "ABCDEFGHIJKLMNOP"

# Pool worker processes receive the puzzle once via initializer (not per-task).
_pool_puzzle: PuzzleSet | None = None


def _init_pool(puzzle: PuzzleSet) -> None:
    global _pool_puzzle
    _pool_puzzle = puzzle


# ---------------------------------------------------------------------------
# Public API  (puzzle defaults to PUZZLE_CLASSIC for backward compatibility)
# ---------------------------------------------------------------------------

def solve(
    month: str,
    day: int,
    puzzle: PuzzleSet | None = None,
    workers: int = 1,
) -> list[tuple[int, int]] | None:
    puzzle = _resolve(puzzle)
    available = _prepare(month, day, puzzle)
    remaining = list(range(puzzle.num_pieces))
    if workers == 1:
        return _backtrack(available, remaining, [], puzzle.placements_by_cell)
    return _parallel_first(available, remaining, workers, puzzle)


def solve_with_fixed(
    month: str,
    day: int,
    fixed: list[tuple[int, int]],
    puzzle: PuzzleSet | None = None,
    workers: int = 1,
) -> list[tuple[int, int]] | None:
    puzzle = _resolve(puzzle)
    available = _prepare(month, day, puzzle)
    fixed_pieces: set[int] = set()
    for piece_idx, mask in fixed:
        available &= ~mask
        fixed_pieces.add(piece_idx)
    remaining = [p for p in range(puzzle.num_pieces) if p not in fixed_pieces]
    if workers == 1:
        return _backtrack(available, remaining, list(fixed), puzzle.placements_by_cell)
    return _parallel_first(available, remaining, workers, puzzle)


def solve_all(
    month: str,
    day: int,
    puzzle: PuzzleSet | None = None,
    workers: int = 1,
) -> list[list[tuple[int, int]]]:
    puzzle = _resolve(puzzle)
    available = _prepare(month, day, puzzle)
    remaining = list(range(puzzle.num_pieces))
    if workers == 1:
        results: list[list[tuple[int, int]]] = []
        _backtrack_all(available, remaining, [], results, puzzle.placements_by_cell)
        return results
    return _parallel_all(available, remaining, workers, puzzle)


def _resolve(puzzle: PuzzleSet | None) -> PuzzleSet:
    if puzzle is not None:
        return puzzle
    from puzzles import PUZZLE_CLASSIC
    return PUZZLE_CLASSIC


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _prepare(month: str, day: int, puzzle: PuzzleSet) -> int:
    if month not in puzzle.months:
        raise ValueError(f"Invalid month '{month}'. Choose from: {puzzle.months}")
    if not (1 <= day <= 31):
        raise ValueError(f"Day must be 1-31, got {day}")

    full_mask = (1 << puzzle.num_cells) - 1
    month_pos = [pos for pos, lbl in puzzle.board.items() if lbl == month]
    day_pos   = [pos for pos, lbl in puzzle.board.items() if lbl == str(day)]

    if not day_pos:
        raise ValueError(f"Day {day} not found on board.")

    exposed = 0
    for pos in month_pos + day_pos:
        exposed |= 1 << puzzle.cell_to_idx[pos]

    return full_mask & ~exposed


# ---------------------------------------------------------------------------
# Single-threaded backtracking
# ---------------------------------------------------------------------------

def _backtrack(
    available: int,
    remaining: list[int],
    placed: list[tuple[int, int]],
    placements_by_cell: list[list[list[int]]],
) -> list[tuple[int, int]] | None:
    if not remaining:
        return placed if available == 0 else None

    target_bit = (available & -available).bit_length() - 1

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                result = _backtrack(
                    available ^ mask, rest,
                    placed + [(piece_idx, mask)],
                    placements_by_cell,
                )
                if result is not None:
                    return result

    return None


def _backtrack_all(
    available: int,
    remaining: list[int],
    placed: list[tuple[int, int]],
    results: list,
    placements_by_cell: list[list[list[int]]],
) -> None:
    if not remaining:
        if available == 0:
            results.append(list(placed))
        return

    target_bit = (available & -available).bit_length() - 1

    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                placed.append((piece_idx, mask))
                _backtrack_all(available ^ mask, rest, placed, results, placements_by_cell)
                placed.pop()


# ---------------------------------------------------------------------------
# Parallel helpers
# ---------------------------------------------------------------------------

def _top_level_tasks(
    available: int,
    remaining: list[int],
    placements_by_cell: list[list[list[int]]],
) -> list[tuple]:
    target_bit = (available & -available).bit_length() - 1
    tasks = []
    for i, piece_idx in enumerate(remaining):
        rest = remaining[:i] + remaining[i + 1:]
        for mask in placements_by_cell[piece_idx][target_bit]:
            if (mask & available) == mask:
                tasks.append((available ^ mask, rest, [(piece_idx, mask)]))
    return tasks


def _worker_first(args: tuple) -> list[tuple[int, int]] | None:
    available, remaining, placed = args
    return _backtrack(available, remaining, placed, _pool_puzzle.placements_by_cell)


def _worker_all(args: tuple) -> list[list[tuple[int, int]]]:
    available, remaining, placed = args
    results: list = []
    _backtrack_all(available, remaining, placed, results, _pool_puzzle.placements_by_cell)
    return results


def _parallel_first(
    available: int, remaining: list[int], workers: int, puzzle: PuzzleSet
) -> list[tuple[int, int]] | None:
    tasks = _top_level_tasks(available, remaining, puzzle.placements_by_cell)
    with Pool(workers, initializer=_init_pool, initargs=(puzzle,)) as pool:
        for result in pool.imap_unordered(_worker_first, tasks, chunksize=4):
            if result is not None:
                pool.terminate()
                return result
    return None


def _parallel_all(
    available: int, remaining: list[int], workers: int, puzzle: PuzzleSet
) -> list[list[tuple[int, int]]]:
    tasks = _top_level_tasks(available, remaining, puzzle.placements_by_cell)
    with Pool(workers, initializer=_init_pool, initargs=(puzzle,)) as pool:
        groups = pool.map(_worker_all, tasks, chunksize=2)
    return [sol for group in groups for sol in group]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_solution(
    solution: list[tuple[int, int]],
    month: str,
    day: int,
    puzzle: PuzzleSet | None = None,
) -> None:
    puzzle = _resolve(puzzle)
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

    print(f"\nSolution for {month} {day}:\n")
    print("     " + "  ".join(f"C{c}" for c in range(puzzle.cols)))
    print("     " + "-" * (puzzle.cols * 5 - 1))
    for r in range(puzzle.rows):
        parts = []
        for c in range(puzzle.cols):
            if (r, c) in puzzle.invalid:
                parts.append("  -- ")
            elif (r, c) in exposed_cells:
                parts.append(f"{GREEN}{puzzle.board[(r, c)]:>4} {RESET}")
            else:
                parts.append(f"{cell_char.get((r, c), '?'):>4} ")
        print(f"R{r} | {''.join(parts)}")

    print("\nLegend:")
    for piece_idx, _ in sorted(solution, key=lambda x: x[0]):
        print(f"  {PIECE_CHARS[piece_idx]} = P{piece_idx}  ({puzzle.piece_sizes[piece_idx]} cells)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from puzzles import PUZZLE_CLASSIC, PUZZLE_B

    parser = argparse.ArgumentParser(description="Calendar Puzzle Solver")
    parser.add_argument("month", help="Month label")
    parser.add_argument("day", type=int, help="Day number (1-31)")
    parser.add_argument("--puzzle", choices=["classic", "puzzle_b"], default="classic")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    pz = PUZZLE_CLASSIC if args.puzzle == "classic" else PUZZLE_B

    print(f"Solving {args.month} {args.day} ({args.puzzle}) with {args.workers} worker(s)...")
    t0 = time.perf_counter()
    solution = solve(args.month, args.day, pz, workers=args.workers)
    elapsed = time.perf_counter() - t0

    if solution is None:
        print("No solution found.")
        sys.exit(1)

    print_solution(solution, args.month, args.day, pz)
    print(f"\nSolved in {elapsed:.3f}s")
