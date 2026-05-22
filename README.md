# pinesweeper

Minesweeper in pygame.

## Run

```
pip install pygame
python main.py
```

## Controls

- Left-click reveals, right-click flags
- Double-click a number to chord-reveal neighbors
- `R` resets the current board
- `B` / `I` / `E` switch difficulty (Beginner 9×9/10, Intermediate 16×16/40, Expert 16×30/99)
- `S` or click the W-L line to toggle stats overlay

Wins/losses are stored per-difficulty in `stats.json` (gitignored).
