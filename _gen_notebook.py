"""Gera o callendar_puzzle.ipynb."""
import json

def md_cell(id_, src):
    return {"cell_type": "markdown", "id": id_, "metadata": {}, "source": src}

def code_cell(id_, src):
    return {"cell_type": "code", "execution_count": None, "id": id_,
            "metadata": {}, "outputs": [], "source": src}

cells = [

    md_cell("md0", (
        "# Calendar Puzzle Solver\n\n"
        "Quebra-cabeça de madeira com **8 peças** num tabuleiro **7×8**.\n"
        "O objetivo é cobrir todas as células, deixando expostos apenas o **mês** e o **dia** desejados.\n\n"
        "| | |\n|---|---|\n"
        "| Tabuleiro | 7 linhas × 8 colunas = **55 células válidas** |\n"
        "| Meses | Jan–Dez, cada um ocupa 2 células (total: 24) |\n"
        "| Dias | 1–31, cada um ocupa 1 célula (total: 31) |\n"
        "| Peças | 8 peças que cobrem **52 células** (55 − 2 do mês − 1 do dia) |"
    )),

    code_cell("c0", (
        "import sys, time\n"
        r"sys.path.insert(0, r'c:\Users\Gustavo\Desktop\calendar-puzzle-solver')" + "\n\n"
        "import matplotlib.pyplot as plt\n"
        "import matplotlib.patches as patches\n\n"
        "from board import BOARD, MONTHS, ROWS, COLS, INVALID, NUM_CELLS, CELL_TO_IDX, IDX_TO_CELL\n"
        "from pieces import PIECES_RAW, ALL_PLACEMENTS, PLACEMENTS_BY_CELL, NUM_PIECES, PIECE_SIZES, all_orientations\n"
        "from solver import solve\n\n"
        "print('Tudo carregado!')"
    )),

    md_cell("md1", "## 1. O Tabuleiro"),

    code_cell("c1", (
        "for r in range(ROWS):\n"
        "    row = []\n"
        "    for c in range(COLS):\n"
        "        if (r, c) in INVALID:\n"
        "            row.append(' -- ')\n"
        "        else:\n"
        "            row.append(f\"{BOARD.get((r, c), ''):>4}\")\n"
        "    print(' '.join(row))\n\n"
        "print(f'\\nTotal de células válidas: {NUM_CELLS}')"
    )),

    md_cell("md2", "## 2. As 8 Peças"),

    code_cell("c2", (
        "PIECE_SHAPES = [\n"
        "    'oooo\\n oo ',\n"
        "    'ooo\\nooo\\n  o',\n"
        "    'oooo\\nooo ',\n"
        "    'ooo\\nooo',\n"
        "    'o\\no\\no\\no\\nooo',\n"
        "    'o\\no\\no\\noooo',\n"
        "    'o  \\nooo\\noo ',\n"
        "    'oooo\\noo  ',\n"
        "]\n\n"
        "for i, (shape, size) in enumerate(zip(PIECE_SHAPES, PIECE_SIZES)):\n"
        "    n_orient = len(all_orientations(PIECES_RAW[i]))\n"
        "    n_pos    = len(ALL_PLACEMENTS[i])\n"
        "    print(f'P{i} | {size} células | {n_orient} orientações | {n_pos} posições válidas')\n"
        "    print(shape)\n"
        "    print()"
    )),

    md_cell("md3", (
        "## 3. Solver — Primeira Solução\n\n"
        "O algoritmo usa **backtracking** com **bitmasks de 55 bits** para representar quais células estão livres.\n"
        "A heurística do *primeiro bit livre* força sempre tentar cobrir a célula mais à esquerda/topo,"
        " podando drasticamente a árvore de busca."
    )),

    code_cell("c3", (
        "PIECE_COLORS = ['#E74C3C','#3498DB','#2ECC71','#F39C12',\n"
        "                '#9B59B6','#1ABC9C','#E67E22','#2980B9']\n\n"
        "def draw_solution(solution, month, day, ax=None, title=None):\n"
        "    standalone = ax is None\n"
        "    if standalone:\n"
        "        fig, ax = plt.subplots(figsize=(9, 6))\n\n"
        "    exposed = {pos for pos, lbl in BOARD.items()\n"
        "               if lbl == month or lbl == str(day)}\n"
        "    cell_piece = {}\n"
        "    for pi, mask in solution:\n"
        "        for bit in range(NUM_CELLS):\n"
        "            if mask & (1 << bit):\n"
        "                cell_piece[IDX_TO_CELL[bit]] = pi\n\n"
        "    ax.set_xlim(0, COLS); ax.set_ylim(0, ROWS)\n"
        "    ax.set_aspect('equal'); ax.invert_yaxis(); ax.axis('off')\n"
        "    if title: ax.set_title(title, fontweight='bold', fontsize=12)\n\n"
        "    for r in range(ROWS):\n"
        "        for c in range(COLS):\n"
        "            lbl = BOARD.get((r, c), '')\n"
        "            if (r, c) in INVALID:\n"
        "                ax.add_patch(patches.Rectangle((c,r),1,1,fc='#2C3E50',ec='#1A252F'))\n"
        "                ax.text(c+.5,r+.5,'×',ha='center',va='center',color='#566573')\n"
        "                continue\n"
        "            if (r, c) in exposed:\n"
        "                fc, tc, ec, lw = '#FDFEFE', '#1E8449', '#27AE60', 2.5\n"
        "            elif (r, c) in cell_piece:\n"
        "                fc = PIECE_COLORS[cell_piece[(r,c)]]\n"
        "                h = fc.lstrip('#')\n"
        "                lum = 0.299*int(h[0:2],16)+0.587*int(h[2:4],16)+0.114*int(h[4:6],16)\n"
        "                tc = 'white' if lum < 140 else '#2C3E50'\n"
        "                ec, lw = '#BDC3C7', 1\n"
        "            else:\n"
        "                fc, tc, ec, lw = '#ECF0F1', '#95A5A6', '#BDC3C7', 1\n"
        "            ax.add_patch(patches.Rectangle((c,r),1,1,fc=fc,ec=ec,lw=lw))\n"
        "            ax.text(c+.5,r+.5,lbl,ha='center',va='center',\n"
        "                    fontsize=9,fontweight='bold',color=tc)\n\n"
        "    for r in range(ROWS):\n"
        "        for c in range(COLS):\n"
        "            if (r,c) not in cell_piece: continue\n"
        "            pi = cell_piece[(r,c)]\n"
        "            if cell_piece.get((r,c+1)) != pi: ax.plot([c+1,c+1],[r,r+1],color='#5D6D7E',lw=2)\n"
        "            if cell_piece.get((r+1,c)) != pi: ax.plot([c,c+1],[r+1,r+1],color='#5D6D7E',lw=2)\n\n"
        "    if standalone:\n"
        "        plt.tight_layout(); plt.show()"
    )),

    code_cell("c4", (
        "MONTH, DAY = 'Abr', 30\n\n"
        "t0 = time.perf_counter()\n"
        "solution = solve(MONTH, DAY)\n"
        "elapsed  = time.perf_counter() - t0\n\n"
        "print(f'Solução para {MONTH} {DAY} encontrada em {elapsed*1000:.1f} ms')\n"
        "draw_solution(solution, MONTH, DAY, title=f'Solução: {MONTH} {DAY}')"
    )),

    md_cell("md4", "## 4. Todas as Soluções para uma Data"),

    code_cell("c5", (
        "FULL_MASK = (1 << NUM_CELLS) - 1\n\n"
        "def solve_all(month, day):\n"
        "    \"\"\"Encontra todas as soluções para o mês e dia dados.\"\"\"\n"
        "    exposed = 0\n"
        "    for pos, lbl in BOARD.items():\n"
        "        if lbl == month or lbl == str(day):\n"
        "            exposed |= 1 << CELL_TO_IDX[pos]\n\n"
        "    available = FULL_MASK & ~exposed\n"
        "    solutions = []\n\n"
        "    def backtrack(avail, remaining, placed):\n"
        "        if not remaining:\n"
        "            if avail == 0:\n"
        "                solutions.append(list(placed))\n"
        "            return\n"
        "        target = (avail & -avail).bit_length() - 1\n"
        "        for i, pi in enumerate(remaining):\n"
        "            rest = remaining[:i] + remaining[i+1:]\n"
        "            for mask in PLACEMENTS_BY_CELL[pi][target]:\n"
        "                if (mask & avail) == mask:\n"
        "                    placed.append((pi, mask))\n"
        "                    backtrack(avail ^ mask, rest, placed)\n"
        "                    placed.pop()\n\n"
        "    backtrack(available, list(range(NUM_PIECES)), [])\n"
        "    return solutions"
    )),

    code_cell("c6", (
        "MONTH, DAY = 'Jan', 1\n\n"
        "t0 = time.perf_counter()\n"
        "all_sols = solve_all(MONTH, DAY)\n"
        "elapsed  = time.perf_counter() - t0\n\n"
        "print(f'{MONTH} {DAY}: {len(all_sols)} soluções em {elapsed:.2f}s')\n\n"
        "fig, axes = plt.subplots(1, 4, figsize=(20, 5))\n"
        "for i, ax in enumerate(axes):\n"
        "    draw_solution(all_sols[i], MONTH, DAY, ax=ax, title=f'Solução {i+1}')\n"
        "plt.suptitle(f'{MONTH} {DAY} — primeiras 4 de {len(all_sols)} soluções', fontsize=14)\n"
        "plt.tight_layout()\n"
        "plt.show()"
    )),

    md_cell("md5", "## 5. Quantas soluções por dia em um mês?"),

    code_cell("c7", (
        "TARGET_MONTH = 'Jan'\n"
        "counts = {}\n\n"
        "for day in range(1, 32):\n"
        "    counts[day] = len(solve_all(TARGET_MONTH, day))\n"
        "    print(f'  {TARGET_MONTH} {day:2d}: {counts[day]} soluções')\n\n"
        "fig, ax = plt.subplots(figsize=(12, 4))\n"
        "bars = ax.bar(list(counts.keys()), list(counts.values()),\n"
        "              color='#3498DB', edgecolor='white')\n"
        "ax.bar_label(bars, fontsize=8)\n"
        "ax.set_xlabel('Dia'); ax.set_ylabel('Número de soluções')\n"
        "ax.set_title(f'Soluções por dia — {TARGET_MONTH}', fontsize=14, fontweight='bold')\n"
        "ax.set_xticks(list(counts.keys()))\n"
        "plt.tight_layout(); plt.show()"
    )),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.11.0",
        },
    },
    "cells": cells,
}

with open("callendar_puzzle.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Notebook gerado com sucesso.")
