# Calendar Puzzle Solver

Solver para o quebra-cabeça de madeira com **8 peças** num tabuleiro **7×8**.  
O objetivo é cobrir todas as células, deixando expostos apenas o **mês** e o **dia** desejados.

## Estrutura

| Arquivo | Função |
|---|---|
| `board.py` | Definição do tabuleiro (meses, dias, células inválidas) |
| `pieces.py` | Peças e geração de todas as orientações/posições válidas |
| `solver.py` | Algoritmo de backtracking com bitmasks (suporte a múltiplos workers) |
| `gui.py` | Interface gráfica |
| `callendar_puzzle.ipynb` | Notebook com exemplos, visualizações e heatmap anual |

## Como usar

### Notebook

Abra `callendar_puzzle.ipynb` e execute as células. Ajuste `MONTH`, `DAY` e `WORKERS` conforme necessário.

### Python

```python
from solver import solve, solve_all

# Primeira solução
solution = solve('Abr', 30)

# Todas as soluções
solutions = solve_all('Jan', 1, workers=4)
print(f'{len(solutions)} soluções encontradas')
```

## Algoritmo

Backtracking com **bitmasks de 55 bits** representando as células livres.  
A heurística do *primeiro bit livre* (célula mais à esquerda/topo) poda drasticamente a árvore de busca.  
Suporte a paralelismo via `workers` para enumerar todas as soluções mais rapidamente.

## Dependências

```
pip install matplotlib numpy tqdm
```
