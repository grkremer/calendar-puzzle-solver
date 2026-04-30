MONTHS = [
    'Jan', 'Fev', 'Mar', 'Abr',
    'Mai', 'Jun', 'Jul', 'Ago',
    'Set', 'Out', 'Nov', 'Dez',
]

ROWS = 7
COLS = 8
INVALID = {(6, 7)}  # célula inválida: canto inferior direito


def build_board() -> dict[tuple[int, int], str]:
    """Retorna mapa (linha, coluna) -> rótulo para todas as células válidas."""
    board: dict[tuple[int, int], str] = {}

    # Linhas 0-2: meses (cada mês ocupa 2 colunas consecutivas, 4 meses por linha)
    for row in range(3):
        for col in range(COLS):
            month_idx = row * 4 + col // 2
            board[(row, col)] = MONTHS[month_idx]

    # Linhas 3-6: dias 1-31
    day = 1
    for row in range(3, ROWS):
        for col in range(COLS):
            if (row, col) in INVALID:
                continue
            board[(row, col)] = str(day)
            day += 1

    return board


BOARD = build_board()

# Índice plano: cada célula válida recebe um inteiro 0..54
CELL_TO_IDX: dict[tuple[int, int], int] = {
    cell: i for i, cell in enumerate(sorted(BOARD))
}
IDX_TO_CELL: dict[int, tuple[int, int]] = {v: k for k, v in CELL_TO_IDX.items()}
NUM_CELLS = len(BOARD)  # 55


def print_board(highlight: set[tuple[int, int]] | None = None) -> None:
    highlight = highlight or set()
    header = "     " + "  ".join(f"C{c}" for c in range(COLS))
    print(header)
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


if __name__ == "__main__":
    print(f"Células válidas: {NUM_CELLS}  (meses: 24, dias: 31)\n")
    print_board()

    # Verificação rápida
    assert NUM_CELLS == 55
    assert all(m in BOARD.values() for m in MONTHS)
    assert "31" in BOARD.values()
    assert (6, 7) not in BOARD
    print("\nVerificações OK.")
