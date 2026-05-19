from __future__ import annotations
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from puzzles import PUZZLE_CLASSIC
from puzzle_set import all_orientations
from solver import solve_with_fixed

# Active puzzle for the GUI (classic only; web app supports both)
_pz = PUZZLE_CLASSIC

# Module-level aliases so the class body stays readable
BOARD       = _pz.board
MONTHS      = _pz.months
ROWS        = _pz.rows
COLS        = _pz.cols
INVALID     = _pz.invalid
NUM_CELLS   = _pz.num_cells
CELL_TO_IDX = _pz.cell_to_idx
IDX_TO_CELL = _pz.idx_to_cell
PIECES_RAW  = _pz.pieces_raw
PIECE_SIZES = _pz.piece_sizes
NUM_PIECES  = _pz.num_pieces
PIECE_COLORS = _pz.piece_colors

# ── visual constants ─────────────────────────────────────────────────────────
CELL      = 70
PAD       = 14
MINI_CELL = 11
MINI_SIZE = 66

EMPTY_BG    = "#ECF0F1"
INVALID_BG  = "#2C3E50"
BORDER_CLR  = "#BDC3C7"
TEXT_DARK   = "#2C3E50"
TEXT_LIGHT  = "#FDFEFE"
EXPOSED_BG  = "#FDFEFE"
EXPOSED_FG  = "#1E8449"
EXPOSED_EC  = "#27AE60"


def _is_dark(h: str) -> bool:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b < 140


def _lighten(h: str, f: float = 0.55) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r + (255 - r) * f), int(g + (255 - g) * f), int(b + (255 - b) * f)
    )


def _sorted_orientations(piece_idx: int) -> list[frozenset]:
    return sorted(all_orientations(PIECES_RAW[piece_idx]),
                  key=lambda s: sorted(s))


# ── main app ─────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Calendar Puzzle Solver")
        self.resizable(False, False)
        self.configure(bg="#F0F3F4")

        self._solution: list[tuple[int, int]] | None = None
        self._placed:   list[tuple[int, int]] = []

        self._selected:     int | None = None
        self._orient_idx:   int = 0
        self._orientations: list[frozenset] = []
        self._hover_rc:     tuple[int, int] | None = None

        self._build_ui()
        self._refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg="#F0F3F4", padx=PAD, pady=PAD)
        outer.pack()

        tk.Label(outer, text="Calendar Puzzle Solver",
                 font=("Helvetica", 18, "bold"),
                 bg="#F0F3F4", fg=TEXT_DARK).grid(row=0, column=0,
                                                   columnspan=2, pady=(0, 12))

        cw = COLS * CELL + 2
        ch = ROWS * CELL + 2
        self.canvas = tk.Canvas(outer, width=cw, height=ch,
                                bg="white", highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=1, column=0, padx=(0, 18), sticky="n")
        self.canvas.bind("<Motion>",   self._on_motion)
        self.canvas.bind("<Leave>",    self._on_leave)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        panel = tk.Frame(outer, bg="#F0F3F4")
        panel.grid(row=1, column=1, sticky="n")
        self._build_controls(panel)

        self.status_var = tk.StringVar(value="Selecione uma peça para colocar no tabuleiro.")
        tk.Label(outer, textvariable=self.status_var, font=("Helvetica", 10),
                 bg="#F0F3F4", fg="#566573", anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_controls(self, parent: tk.Frame) -> None:
        def sep() -> None:
            tk.Frame(parent, bg="#D5D8DC", height=1).pack(fill="x", pady=8)

        def lbl(text: str) -> None:
            tk.Label(parent, text=text, font=("Helvetica", 10, "bold"),
                     bg="#F0F3F4", fg=TEXT_DARK, anchor="w").pack(fill="x", pady=(6, 2))

        lbl("Mês")
        self.month_var = tk.StringVar(value=MONTHS[0])
        ttk.Combobox(parent, textvariable=self.month_var, values=MONTHS,
                     state="readonly", width=14).pack()

        lbl("Dia")
        self.day_var = tk.StringVar(value="1")
        ttk.Combobox(parent, textvariable=self.day_var,
                     values=[str(d) for d in range(1, 32)],
                     state="readonly", width=14).pack()

        self.solve_btn = tk.Button(
            parent, text="Resolver", font=("Helvetica", 11, "bold"),
            bg="#2980B9", fg="white", activebackground="#1F618D",
            relief="flat", padx=10, pady=6, cursor="hand2",
            command=self._on_solve)
        self.solve_btn.pack(fill="x", pady=(10, 0))

        sep()

        tk.Label(parent, text="Peças  (clique para selecionar)",
                 font=("Helvetica", 10, "bold"),
                 bg="#F0F3F4", fg=TEXT_DARK).pack(anchor="w")

        grid = tk.Frame(parent, bg="#F0F3F4")
        grid.pack(pady=(4, 0))
        self._piece_btns: list[tk.Canvas] = []
        for i in range(NUM_PIECES):
            row_f, col_f = divmod(i, 4)
            c = tk.Canvas(grid, width=MINI_SIZE, height=MINI_SIZE,
                          bg="#F0F3F4", highlightthickness=2,
                          highlightbackground=BORDER_CLR, cursor="hand2")
            c.grid(row=row_f, column=col_f, padx=3, pady=3)
            c.bind("<Button-1>", lambda e, idx=i: self._on_piece_btn(idx))
            self._piece_btns.append(c)

        orient_row = tk.Frame(parent, bg="#F0F3F4")
        orient_row.pack(fill="x", pady=(8, 0))

        self.rotate_btn = tk.Button(
            orient_row, text="↺  Rotacionar", font=("Helvetica", 10),
            bg="#ECF0F1", relief="flat", padx=8, pady=4, cursor="hand2",
            command=self._on_rotate, state="disabled")
        self.rotate_btn.pack(side="left")

        self.orient_lbl = tk.Label(orient_row, text="", font=("Helvetica", 9),
                                   bg="#F0F3F4", fg="#7F8C8D", width=6)
        self.orient_lbl.pack(side="left", padx=(6, 0))

        sep()

        action_row = tk.Frame(parent, bg="#F0F3F4")
        action_row.pack(fill="x")

        self.undo_btn = tk.Button(
            action_row, text="↩ Desfazer", font=("Helvetica", 10),
            bg="#ECF0F1", relief="flat", padx=8, pady=4, cursor="hand2",
            command=self._on_undo, state="disabled")
        self.undo_btn.pack(side="left", padx=(0, 6))

        tk.Button(action_row, text="🗑 Limpar tudo", font=("Helvetica", 10),
                  bg="#ECF0F1", relief="flat", padx=8, pady=4, cursor="hand2",
                  command=self._on_reset).pack(side="left")

        sep()

        self.legend_frame = tk.Frame(parent, bg="#F0F3F4")
        self.legend_frame.pack(fill="x")

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _cell_bbox(self, r: int, c: int) -> tuple[int, int, int, int]:
        x1 = 1 + c * CELL
        y1 = 1 + r * CELL
        return x1, y1, x1 + CELL, y1 + CELL

    def _rc_from_xy(self, x: int, y: int) -> tuple[int, int] | None:
        r, c = (y - 1) // CELL, (x - 1) // CELL
        if 0 <= r < ROWS and 0 <= c < COLS:
            return r, c
        return None

    # ── placement helpers ─────────────────────────────────────────────────────

    def _current_shape(self) -> list[tuple[int, int]] | None:
        if self._selected is None or not self._orientations:
            return None
        return list(self._orientations[self._orient_idx])

    def _hover_cells(self) -> list[tuple[int, int]] | None:
        shape = self._current_shape()
        if shape is None or self._hover_rc is None:
            return None
        hr, hc = self._hover_rc
        return [(hr + r, hc + c) for r, c in shape]

    def _occupied_mask(self) -> int:
        m = 0
        for _, mask in self._placed:
            m |= mask
        return m

    def _exposed_mask(self) -> int:
        month = self.month_var.get()
        day   = int(self.day_var.get())
        exposed = 0
        for pos, lbl in BOARD.items():
            if lbl == month or lbl == str(day):
                exposed |= 1 << CELL_TO_IDX[pos]
        return exposed

    def _is_valid_placement(self, cells: list[tuple[int, int]]) -> bool:
        blocked = self._occupied_mask() | self._exposed_mask()
        for rc in cells:
            if rc not in CELL_TO_IDX:
                return False
            if (1 << CELL_TO_IDX[rc]) & blocked:
                return False
        return True

    def _mask_from_cells(self, cells: list[tuple[int, int]]) -> int:
        m = 0
        for rc in cells:
            m |= 1 << CELL_TO_IDX[rc]
        return m

    def _piece_at(self, r: int, c: int) -> int | None:
        if (r, c) not in CELL_TO_IDX:
            return None
        bit = 1 << CELL_TO_IDX[(r, c)]
        for i, (_, mask) in enumerate(self._placed):
            if mask & bit:
                return i
        return None

    def _used_pieces(self) -> set[int]:
        return {pi for pi, _ in self._placed}

    # ── drawing ───────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._draw_board()
        self._draw_piece_buttons()
        self._update_controls()

    def _draw_board(self) -> None:
        self.canvas.delete("all")

        month = self.month_var.get()
        day   = int(self.day_var.get())
        exposed = {pos for pos, lbl in BOARD.items()
                   if lbl == month or lbl == str(day)}

        cell_piece: dict[tuple[int, int], int] = {}
        source = self._solution if self._solution else self._placed
        for pi, mask in source:
            for bit in range(NUM_CELLS):
                if mask & (1 << bit):
                    cell_piece[IDX_TO_CELL[bit]] = pi

        hcells = self._hover_cells()
        hover_valid = hcells is not None and self._is_valid_placement(hcells)
        hover_set   = set(map(tuple, hcells)) if hcells else set()

        for r in range(ROWS):
            for c in range(COLS):
                x1, y1, x2, y2 = self._cell_bbox(r, c)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                lbl = BOARD.get((r, c), "")

                if (r, c) in INVALID:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill=INVALID_BG, outline="#1A252F")
                    self.canvas.create_text(cx, cy, text="×",
                                            fill="#566573", font=("Helvetica", 14))
                    continue

                if (r, c) in exposed:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill=EXPOSED_BG,
                        outline=EXPOSED_EC, width=2.5)
                    self.canvas.create_text(cx, cy, text=lbl,
                                            fill=EXPOSED_FG,
                                            font=("Helvetica", 10, "bold"))
                    continue

                if (r, c) in hover_set and not self._solution:
                    col = (_lighten(PIECE_COLORS[self._selected], 0.35)
                           if hover_valid else "#F1948A")
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill=col, outline=BORDER_CLR)
                    self.canvas.create_text(cx, cy, text=lbl, fill=TEXT_DARK,
                                            font=("Helvetica", 9, "bold"))
                    continue

                if (r, c) in cell_piece:
                    bg = PIECE_COLORS[cell_piece[(r, c)]]
                    fg = TEXT_LIGHT if _is_dark(bg) else TEXT_DARK
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill=bg, outline=BORDER_CLR)
                    self.canvas.create_text(cx, cy, text=lbl, fill=fg,
                                            font=("Helvetica", 9, "bold"))
                    continue

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=EMPTY_BG, outline=BORDER_CLR)
                self.canvas.create_text(cx, cy, text=lbl, fill="#7F8C8D",
                                        font=("Helvetica", 9))

        for r in range(ROWS):
            for c in range(COLS):
                if (r, c) not in cell_piece:
                    continue
                pi = cell_piece[(r, c)]
                x1, y1, x2, y2 = self._cell_bbox(r, c)
                if cell_piece.get((r, c + 1)) != pi:
                    self.canvas.create_line(x2, y1, x2, y2,
                                            fill="#5D6D7E", width=2)
                if cell_piece.get((r + 1, c)) != pi:
                    self.canvas.create_line(x1, y2, x2, y2,
                                            fill="#5D6D7E", width=2)

    def _draw_piece_buttons(self) -> None:
        used = self._used_pieces()
        for i, canvas in enumerate(self._piece_btns):
            self._draw_one_btn(canvas, i,
                               selected=(i == self._selected),
                               used=(i in used))

    def _draw_one_btn(self, canvas: tk.Canvas, idx: int,
                      selected: bool, used: bool) -> None:
        canvas.delete("all")
        color = "#BDC3C7" if used else PIECE_COLORS[idx]
        canvas.configure(
            highlightbackground="#2980B9" if selected else BORDER_CLR,
            highlightthickness=2 if selected else 1,
        )

        shape = sorted(all_orientations(PIECES_RAW[idx]))[0]
        cells = list(shape)
        if not cells:
            return
        min_r = min(r for r, c in cells)
        min_c = min(c for r, c in cells)
        max_r = max(r for r, c in cells)
        max_c = max(c for r, c in cells)
        h = max_r - min_r + 1
        w = max_c - min_c + 1
        off_r = (MINI_SIZE - h * MINI_CELL) // 2
        off_c = (MINI_SIZE - w * MINI_CELL) // 2

        for r, c in cells:
            x1 = off_c + (c - min_c) * MINI_CELL
            y1 = off_r + (r - min_r) * MINI_CELL
            canvas.create_rectangle(x1, y1,
                                    x1 + MINI_CELL, y1 + MINI_CELL,
                                    fill=color, outline="white", width=1)

        lbl = f"P{idx}"
        if used:
            lbl += " ✓"
        canvas.create_text(MINI_SIZE // 2, MINI_SIZE - 7, text=lbl,
                           font=("Helvetica", 7), fill="#7F8C8D")

    def _update_controls(self) -> None:
        has_sel  = self._selected is not None
        has_plcd = bool(self._placed)

        self.rotate_btn.config(state="normal" if has_sel else "disabled")
        self.undo_btn.config(state="normal" if has_plcd else "disabled")

        if has_sel and self._orientations:
            n = len(self._orientations)
            self.orient_lbl.config(text=f"{self._orient_idx + 1}/{n}")
        else:
            self.orient_lbl.config(text="")

    def _draw_legend(self, solution: list[tuple[int, int]]) -> None:
        for w in self.legend_frame.winfo_children():
            w.destroy()
        tk.Label(self.legend_frame, text="Peças na solução:",
                 font=("Helvetica", 9, "bold"),
                 bg="#F0F3F4", fg=TEXT_DARK).pack(anchor="w", pady=(4, 2))
        for pi, _ in sorted(solution):
            row = tk.Frame(self.legend_frame, bg="#F0F3F4")
            row.pack(anchor="w", pady=1)
            tk.Frame(row, bg=PIECE_COLORS[pi], width=16, height=16,
                     relief="flat").pack(side="left", padx=(0, 6))
            tk.Label(row, text=f"P{pi}  ({PIECE_SIZES[pi]} células)",
                     font=("Helvetica", 9), bg="#F0F3F4",
                     fg=TEXT_DARK).pack(side="left")

    # ── event handlers ────────────────────────────────────────────────────────

    def _on_motion(self, event: tk.Event) -> None:
        rc = self._rc_from_xy(event.x, event.y)
        if rc != self._hover_rc:
            self._hover_rc = rc
            if self._selected is not None and not self._solution:
                self._draw_board()

    def _on_leave(self, _: tk.Event) -> None:
        if self._hover_rc is not None:
            self._hover_rc = None
            if self._selected is not None and not self._solution:
                self._draw_board()

    def _on_click(self, event: tk.Event) -> None:
        if self._selected is None or self._solution:
            return
        cells = self._hover_cells()
        if cells is None or not self._is_valid_placement(cells):
            return
        mask = self._mask_from_cells(cells)
        self._placed.append((self._selected, mask))
        self._selected = None
        self._orientations = []
        self._hover_rc = None
        self.canvas.configure(cursor="crosshair")
        self._refresh()
        self.status_var.set(
            f"Peça colocada. {8 - len(self._placed)} peça(s) restante(s) para o solver.")

    def _on_right_click(self, event: tk.Event) -> None:
        if self._solution:
            return
        rc = self._rc_from_xy(event.x, event.y)
        if rc is None:
            return
        idx = self._piece_at(*rc)
        if idx is not None:
            pi, _ = self._placed.pop(idx)
            self._refresh()
            self.status_var.set(f"P{pi} removida.")

    def _on_piece_btn(self, idx: int) -> None:
        if idx in self._used_pieces():
            return
        if self._selected == idx:
            self._selected = None
            self._orientations = []
        else:
            self._selected    = idx
            self._orient_idx  = 0
            self._orientations = _sorted_orientations(idx)
        self._solution = None
        self._refresh()
        if self._selected is not None:
            self.status_var.set(
                f"P{self._selected} selecionada — clique no tabuleiro para posicionar.")
        else:
            self.status_var.set("Seleção limpa.")

    def _on_rotate(self) -> None:
        if not self._orientations:
            return
        self._orient_idx = (self._orient_idx + 1) % len(self._orientations)
        self._update_controls()
        self._draw_board()

    def _on_undo(self) -> None:
        if self._placed:
            pi, _ = self._placed.pop()
            self._solution = None
            self._refresh()
            self.status_var.set(f"P{pi} removida.")

    def _on_reset(self) -> None:
        self._placed    = []
        self._selected  = None
        self._solution  = None
        self._hover_rc  = None
        self._orientations = []
        self._refresh()
        self.status_var.set("Tabuleiro limpo.")

    def _on_solve(self) -> None:
        month = self.month_var.get()
        day   = int(self.day_var.get())
        self._selected = None
        self._solution = None
        self.solve_btn.config(state="disabled", text="Resolvendo…")
        self.status_var.set("Calculando…")
        self._draw_board()

        fixed = list(self._placed)

        def run() -> None:
            t0       = time.perf_counter()
            solution = solve_with_fixed(month, day, fixed, _pz)
            elapsed  = time.perf_counter() - t0
            self.after(0, lambda: self._on_result(solution, month, day, elapsed))

        threading.Thread(target=run, daemon=True).start()

    def _on_result(self, solution: list | None,
                   month: str, day: int, elapsed: float) -> None:
        self.solve_btn.config(state="normal", text="Resolver")

        if solution is None:
            self.status_var.set("Sem solução com as peças pré-colocadas.")
            messagebox.showwarning("Sem solução",
                                   "Não foi possível resolver com as peças colocadas.\n"
                                   "Tente remover ou mover alguma peça.")
            return

        self._solution = solution
        self.status_var.set(f"Resolvido em {elapsed * 1000:.1f} ms")
        self._refresh()
        self._draw_legend(solution)


if __name__ == "__main__":
    App().mainloop()
