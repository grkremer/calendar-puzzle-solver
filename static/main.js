'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let puzzle      = null;   // current puzzle data from /api/puzzle/<name>
let selPiece    = null;   // selected piece index or null
let orientIdx   = 0;      // current orientation index
let placed      = [];     // [{piece_id, cells: [[r,c],...]}]
let solution    = null;   // [{piece_id, cells}] from API, or null
let hoverCell   = null;   // [r, c] under mouse, or null

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('puzzle-select').addEventListener('change', e => loadPuzzle(e.target.value));
  document.getElementById('month-select').addEventListener('change', refreshBoard);
  document.getElementById('day-select').addEventListener('change', refreshBoard);
  document.getElementById('btn-solve').addEventListener('click', onSolve);
  document.getElementById('btn-rotate').addEventListener('click', onRotate);
  document.getElementById('btn-undo').addEventListener('click', onUndo);
  document.getElementById('btn-reset').addEventListener('click', onReset);
  document.addEventListener('keydown', e => {
    if (e.key === 'r' || e.key === 'R') onRotate();
    if (e.key === 'Escape') selectPiece(null);
  });
  loadPuzzle('classic');
});

// ── Puzzle loading ─────────────────────────────────────────────────────────
async function loadPuzzle(name) {
  setStatus('Carregando…');
  const res = await fetch(`/api/puzzle/${name}`);
  puzzle = await res.json();
  placed = []; solution = null; selPiece = null; orientIdx = 0;

  // month select
  const ms = document.getElementById('month-select');
  ms.innerHTML = puzzle.months.map(m => `<option>${m}</option>`).join('');

  // day select
  const ds = document.getElementById('day-select');
  ds.innerHTML = Array.from({length: 31}, (_, i) => `<option>${i + 1}</option>`).join('');

  buildBoard();
  buildPieceButtons();
  updateControls();
  setStatus('Selecione uma peça ou clique em Resolver.');
}

// ── Board construction ─────────────────────────────────────────────────────
function buildBoard() {
  const el = document.getElementById('board');
  el.innerHTML = '';
  el.style.gridTemplateColumns = `repeat(${puzzle.cols}, 64px)`;
  el.style.gridTemplateRows    = `repeat(${puzzle.rows}, 64px)`;

  for (let r = 0; r < puzzle.rows; r++) {
    for (let c = 0; c < puzzle.cols; c++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.id = `c${r}_${c}`;

      const inv = puzzle.invalid.some(([ir, ic]) => ir === r && ic === c);
      if (inv) {
        cell.classList.add('invalid');
        cell.textContent = '×';
      } else {
        cell.textContent = puzzle.board[`${r},${c}`] || '';
      }

      cell.addEventListener('mouseenter', () => { hoverCell = [r, c]; updatePreview(); });
      cell.addEventListener('mouseleave', () => { hoverCell = null;   clearPreview(); });
      cell.addEventListener('click',      () => onCellClick(r, c));
      cell.addEventListener('contextmenu', e => { e.preventDefault(); onRightClick(r, c); });
      el.appendChild(cell);
    }
  }
}

// ── Board refresh (colours + borders) ─────────────────────────────────────
function refreshBoard() {
  if (!puzzle) return;
  const month = document.getElementById('month-select').value;
  const day   = String(document.getElementById('day-select').value);

  // build cell → piece lookup
  const src = solution || placed;
  const cellPiece = {};
  src.forEach(({piece_id, cells}) =>
    cells.forEach(([r, c]) => { cellPiece[`${r},${c}`] = piece_id; })
  );

  for (let r = 0; r < puzzle.rows; r++) {
    for (let c = 0; c < puzzle.cols; c++) {
      const el = document.getElementById(`c${r}_${c}`);
      if (!el || el.classList.contains('invalid')) continue;

      const key   = `${r},${c}`;
      const label = puzzle.board[key] || '';
      const isExp = label === month || label === day;
      const pid   = cellPiece[key];

      // reset dynamic styles
      el.classList.remove('exposed', 'occupied');
      el.style.backgroundColor = '';
      el.style.color = '';
      el.style.borderRight = el.style.borderBottom = '';

      if (isExp) {
        el.classList.add('exposed');
      } else if (pid !== undefined) {
        el.classList.add('occupied');
        const col = puzzle.pieces[pid].color;
        el.style.backgroundColor = col;
        el.style.color = isDark(col) ? '#fff' : '#2C3E50';
      }
    }
  }

  // thick borders between piece groups
  for (const [key, pid] of Object.entries(cellPiece)) {
    const [r, c] = key.split(',').map(Number);
    const el = document.getElementById(`c${r}_${c}`);
    if (!el) continue;
    if (cellPiece[`${r},${c + 1}`] !== pid) el.style.borderRight  = '2.5px solid #2C3E50';
    if (cellPiece[`${r + 1},${c}`] !== pid) el.style.borderBottom = '2.5px solid #2C3E50';
  }

  updatePreview();
  refreshLegend(src);
}

// ── Hover preview ──────────────────────────────────────────────────────────
function clearPreview() {
  document.querySelectorAll('.preview-valid, .preview-invalid').forEach(el => {
    el.classList.remove('preview-valid', 'preview-invalid');
    el.style.backgroundColor = el._savedBg ?? '';
    el.style.color = el._savedFg ?? '';
    delete el._savedBg; delete el._savedFg;
  });
}

function updatePreview() {
  clearPreview();
  if (selPiece === null || hoverCell === null || solution) return;

  const orient = puzzle.pieces[selPiece].orientations[orientIdx];
  const [hr, hc] = hoverCell;
  const cells = orient.map(([dr, dc]) => [hr + dr, hc + dc]);
  const valid = isPlacementValid(cells);

  cells.forEach(([r, c]) => {
    const el = document.getElementById(`c${r}_${c}`);
    if (!el) return;
    el._savedBg = el.style.backgroundColor;
    el._savedFg = el.style.color;
    if (valid) {
      el.classList.add('preview-valid');
      el.style.backgroundColor = lighten(puzzle.pieces[selPiece].color, 0.38);
      el.style.color = '#2C3E50';
    } else {
      el.classList.add('preview-invalid');
    }
  });
}

function isPlacementValid(cells) {
  const month = document.getElementById('month-select').value;
  const day   = String(document.getElementById('day-select').value);
  const usedKeys = new Set(placed.flatMap(p => p.cells.map(([r, c]) => `${r},${c}`)));

  return cells.every(([r, c]) => {
    const key = `${r},${c}`;
    const label = puzzle.board[key];
    if (label === undefined) return false;           // off-board or invalid
    if (label === month || label === day) return false;
    if (usedKeys.has(key)) return false;
    return true;
  });
}

// ── Piece buttons ──────────────────────────────────────────────────────────
function buildPieceButtons() {
  const grid = document.getElementById('piece-buttons');
  grid.innerHTML = '';
  puzzle.pieces.forEach((piece, i) => {
    const btn = document.createElement('div');
    btn.className = 'piece-btn';
    btn.id = `pb${i}`;
    btn.title = `P${i} · ${piece.size} células`;

    const cvs = document.createElement('canvas');
    cvs.width = cvs.height = 58;
    btn.appendChild(cvs);
    btn.addEventListener('click', () => onPieceBtnClick(i));
    grid.appendChild(btn);
  });
  refreshPieceButtons();
}

function refreshPieceButtons() {
  const usedIds = new Set(placed.map(p => p.piece_id));
  puzzle.pieces.forEach((piece, i) => {
    const btn = document.getElementById(`pb${i}`);
    if (!btn) return;
    const used = usedIds.has(i);
    const sel  = selPiece === i;
    btn.classList.toggle('selected', sel);
    btn.classList.toggle('used', used);
    drawPieceBtn(btn.querySelector('canvas'), piece, used, sel);
  });
}

function drawPieceBtn(cvs, piece, used, selected) {
  const ctx = cvs.getContext('2d');
  const W = cvs.width, H = cvs.height;
  ctx.clearRect(0, 0, W, H);

  const color  = used ? '#BDC3C7' : piece.color;
  const orient = piece.orientations[0];
  const rows   = orient.map(([r]) => r);
  const cols   = orient.map(([, c]) => c);
  const minR = Math.min(...rows), maxR = Math.max(...rows);
  const minC = Math.min(...cols), maxC = Math.max(...cols);
  const h = maxR - minR + 1, w = maxC - minC + 1;
  const S = Math.min(Math.floor((W - 6) / w), Math.floor((H - 14) / h), 15);
  const offR = Math.floor((H - 14 - h * S) / 2);
  const offC = Math.floor((W - w * S) / 2);

  orient.forEach(([r, c]) => {
    ctx.fillStyle = color;
    ctx.fillRect(offC + (c - minC) * S, offR + (r - minR) * S, S - 1, S - 1);
  });

  ctx.fillStyle = '#95A5A6';
  ctx.font = '8px system-ui';
  ctx.textAlign = 'center';
  ctx.fillText(`P${piece.id}${used ? ' ✓' : ''}`, W / 2, H - 3);

  if (selected) {
    ctx.strokeStyle = '#2980B9';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, W - 2, H - 2);
  }
}

// ── Piece selection ────────────────────────────────────────────────────────
function selectPiece(idx) {
  const usedIds = new Set(placed.map(p => p.piece_id));
  if (idx !== null && usedIds.has(idx)) return;
  selPiece = idx;
  orientIdx = 0;
  solution = null;
  refreshPieceButtons();
  updateControls();
  clearPreview();
  if (hoverCell) updatePreview();
}

function onPieceBtnClick(i) {
  selectPiece(selPiece === i ? null : i);
  setStatus(selPiece !== null
    ? `P${selPiece} selecionada · clique no tabuleiro para posicionar · R para rotacionar`
    : 'Seleção limpa.');
}

function onRotate() {
  if (selPiece === null) return;
  orientIdx = (orientIdx + 1) % puzzle.pieces[selPiece].orientations.length;
  updateControls();
  if (hoverCell) updatePreview();
}

// ── Cell interaction ───────────────────────────────────────────────────────
function onCellClick(r, c) {
  if (selPiece === null || solution) return;
  const orient = puzzle.pieces[selPiece].orientations[orientIdx];
  const cells  = orient.map(([dr, dc]) => [r + dr, c + dc]);
  if (!isPlacementValid(cells)) return;

  placed.push({ piece_id: selPiece, cells });
  const pid = selPiece;
  selectPiece(null);
  refreshBoard();
  setStatus(`P${pid} colocada · ${puzzle.pieces.length - placed.length} peça(s) restante(s).`);
}

function onRightClick(r, c) {
  if (solution) return;
  const key = `${r},${c}`;
  const idx = placed.findIndex(p => p.cells.some(([pr, pc]) => `${pr},${pc}` === key));
  if (idx === -1) return;
  const { piece_id } = placed.splice(idx, 1)[0];
  refreshBoard();
  updateControls();
  setStatus(`P${piece_id} removida.`);
}

// ── Action handlers ────────────────────────────────────────────────────────
function onUndo() {
  if (!placed.length) return;
  const { piece_id } = placed.pop();
  solution = null;
  refreshBoard();
  updateControls();
  setStatus(`P${piece_id} removida.`);
}

function onReset() {
  placed = []; solution = null; selPiece = null; orientIdx = 0;
  refreshBoard();
  refreshPieceButtons();
  updateControls();
  setStatus('Tabuleiro limpo.');
}

async function onSolve() {
  const month = document.getElementById('month-select').value;
  const day   = parseInt(document.getElementById('day-select').value);
  const name  = document.getElementById('puzzle-select').value;

  selPiece = null; solution = null;
  refreshPieceButtons();
  document.getElementById('btn-solve').disabled = true;
  setStatus('Calculando…');
  refreshBoard();

  try {
    const res = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        puzzle: name, month, day,
        fixed: placed.map(({ piece_id, cells }) => ({ piece_id, cells })),
      }),
    });
    const data = await res.json();

    if (data.error) {
      setStatus(`Erro: ${data.error}`);
    } else if (!data.solution) {
      setStatus('Sem solução com as peças pré-colocadas.');
    } else {
      solution = data.solution;
      placed = [];
      refreshBoard();
      setStatus(`Resolvido em ${data.elapsed_ms} ms`);
    }
  } catch (e) {
    setStatus(`Erro de rede: ${e.message}`);
  } finally {
    document.getElementById('btn-solve').disabled = false;
    updateControls();
  }
}

// ── Legend ─────────────────────────────────────────────────────────────────
function refreshLegend(src) {
  const el = document.getElementById('legend');
  if (!src || !src.length) { el.innerHTML = ''; return; }

  const seen = new Set();
  const items = src.filter(({ piece_id }) => {
    if (seen.has(piece_id)) return false;
    seen.add(piece_id);
    return true;
  }).sort((a, b) => a.piece_id - b.piece_id);

  el.innerHTML = `<p class="legend-title">Peças</p>` +
    items.map(({ piece_id }) => {
      const p = puzzle.pieces[piece_id];
      return `<div class="legend-item">
        <div class="legend-swatch" style="background:${p.color}"></div>
        <span>P${piece_id} · ${p.size} células</span>
      </div>`;
    }).join('');
}

// ── Controls state ─────────────────────────────────────────────────────────
function updateControls() {
  document.getElementById('btn-rotate').disabled = selPiece === null;
  document.getElementById('btn-undo').disabled   = placed.length === 0;

  const lbl = document.getElementById('orient-label');
  if (selPiece !== null && puzzle) {
    const n = puzzle.pieces[selPiece].orientations.length;
    lbl.textContent = `${orientIdx + 1}/${n}`;
  } else {
    lbl.textContent = '';
  }
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

// ── Colour utilities ───────────────────────────────────────────────────────
function isDark(hex) {
  const h = hex.replace('#', '');
  return 0.299 * parseInt(h.slice(0, 2), 16)
       + 0.587 * parseInt(h.slice(2, 4), 16)
       + 0.114 * parseInt(h.slice(4, 6), 16) < 140;
}

function lighten(hex, f) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgb(${r + (255 - r) * f | 0},${g + (255 - g) * f | 0},${b + (255 - b) * f | 0})`;
}
