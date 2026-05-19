from __future__ import annotations
import time
from flask import Flask, jsonify, request, send_from_directory
from puzzles import PUZZLE_CLASSIC, PUZZLE_B
from puzzle_set import PuzzleSet, all_orientations
from solver import solve_with_fixed

app = Flask(__name__, static_folder='static', static_url_path='/static')

_PUZZLES: dict[str, PuzzleSet] = {
    'classic':  PUZZLE_CLASSIC,
    'puzzle_b': PUZZLE_B,
}


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/puzzle/<name>')
def get_puzzle(name: str):
    puzzle = _PUZZLES.get(name)
    if puzzle is None:
        return jsonify({'error': f'Unknown puzzle: {name}'}), 404

    board = {f'{r},{c}': label for (r, c), label in puzzle.board.items()}

    pieces = []
    for i, raw in enumerate(puzzle.pieces_raw):
        orients = sorted(
            [sorted(list(o)) for o in all_orientations(raw)],
            key=lambda o: o,
        )
        pieces.append({
            'id': i,
            'color': puzzle.piece_colors[i],
            'size': puzzle.piece_sizes[i],
            'orientations': orients,
        })

    return jsonify({
        'name': puzzle.name,
        'rows': puzzle.rows,
        'cols': puzzle.cols,
        'invalid': [[r, c] for r, c in sorted(puzzle.invalid)],
        'board': board,
        'months': puzzle.months,
        'pieces': pieces,
    })


@app.route('/api/solve', methods=['POST'])
def solve():
    data = request.get_json(force=True)
    name      = data.get('puzzle', 'classic')
    month     = data.get('month', '')
    day       = int(data.get('day', 1))
    fixed_raw = data.get('fixed', [])

    puzzle = _PUZZLES.get(name)
    if puzzle is None:
        return jsonify({'error': f'Unknown puzzle: {name}'}), 404

    fixed: list[tuple[int, int]] = []
    for fp in fixed_raw:
        piece_id = fp['piece_id']
        mask = 0
        for r, c in fp['cells']:
            idx = puzzle.cell_to_idx.get((r, c))
            if idx is None:
                return jsonify({'error': f'Invalid cell ({r},{c})'}), 400
            mask |= 1 << idx
        fixed.append((piece_id, mask))

    t0 = time.perf_counter()
    try:
        solution = solve_with_fixed(month, day, fixed, puzzle)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if solution is None:
        return jsonify({'solution': None, 'elapsed_ms': round(elapsed_ms, 1)})

    result = []
    for piece_id, mask in solution:
        cells = [list(puzzle.idx_to_cell[bit])
                 for bit in range(puzzle.num_cells)
                 if mask & (1 << bit)]
        result.append({'piece_id': piece_id, 'cells': cells})

    return jsonify({'solution': result, 'elapsed_ms': round(elapsed_ms, 1)})


if __name__ == '__main__':
    print('Iniciando servidor em http://0.0.0.0:8001')
    print('Acesse na rede local pelo IP desta máquina na porta 8001')
    app.run(host='0.0.0.0', port=8001, threaded=True)
