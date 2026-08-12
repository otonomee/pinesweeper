# pinesweeper

Minesweeper in pygame — glossy Win7-style tiles, a pinecone in place of the mine, and five swappable color themes.

![Pinesweeper gameplay](docs/img/gameplay.png)

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

Wins/losses and your chosen theme are stored per-difficulty in `stats.json` (gitignored).

## Themes

Switch via **Options → Theme**. Your selection persists across sessions.

| Pine | Classic |
|:---:|:---:|
| ![Pine](docs/img/pine.png) | ![Classic](docs/img/classic.png) |

| Dark | Coastal |
|:---:|:---:|
| ![Dark](docs/img/dark.png) | ![Coastal](docs/img/coastal.png) |

| Deep Ocean | |
|:---:|:---:|
| ![Deep Ocean](docs/img/deep-ocean.png) | |
