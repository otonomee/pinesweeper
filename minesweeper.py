"""Minesweeper in pygame. Left-click reveals, right-click flags,
double-click a number to chord-reveal neighbors.

Difficulties: B = Beginner (9x9, 10), I = Intermediate (16x16, 40),
E = Expert (16x30, 99). Press B/I/E to switch (also resets). Press R to
reset current difficulty. Wins/losses are persisted per-difficulty to
stats.json next to this file."""
import json
import os
import sys
import random
import pygame

CELL = 32
MARGIN_TOP = 72
PAD = 12
DOUBLE_CLICK_MS = 350

DIFFICULTIES = {
    "Beginner":     {"rows": 9,  "cols": 9,  "mines": 10, "key": pygame.K_b, "label": "B"},
    "Intermediate": {"rows": 16, "cols": 16, "mines": 40, "key": pygame.K_i, "label": "I"},
    "Expert":       {"rows": 16, "cols": 30, "mines": 99, "key": pygame.K_e, "label": "E"},
}
DEFAULT_DIFFICULTY = "Intermediate"
STATS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")

# palette
BG = (38, 42, 52)
PANEL = (28, 31, 38)
HIDDEN_TOP = (96, 104, 120)
HIDDEN_BOT = (62, 68, 80)
HIDDEN_HOVER = (112, 122, 140)
REVEALED = (210, 214, 222)
REVEALED_ALT = (198, 202, 212)
GRID_LINE = (150, 154, 162)
TEXT = (235, 238, 245)
SUBTEXT = (170, 176, 188)
ACCENT_OK = (88, 200, 120)
ACCENT_BAD = (235, 90, 90)
ACCENT_SEL = (90, 140, 240)
FLAG_RED = (230, 70, 70)
FLAG_POLE = (40, 40, 48)
MINE_BLACK = (24, 26, 32)
MINE_SHINE = (200, 200, 210)
BOOM = (255, 170, 60)
NUM_COLORS = {
    1: (52, 120, 246),
    2: (52, 168, 83),
    3: (235, 80, 80),
    4: (130, 60, 200),
    5: (190, 90, 30),
    6: (40, 170, 180),
    7: (60, 60, 80),
    8: (130, 130, 140),
}


def load_stats():
    base = {name: {"wins": 0, "losses": 0} for name in DIFFICULTIES}
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name in DIFFICULTIES:
            if isinstance(data.get(name), dict):
                base[name]["wins"] = int(data[name].get("wins", 0))
                base[name]["losses"] = int(data[name].get("losses", 0))
    except (FileNotFoundError, ValueError, OSError):
        pass
    return base


def save_stats(stats):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except OSError:
        pass


class Board:
    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.mines_count = mines
        self.reset()

    def reset(self):
        self.mines = set()
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        self.flagged = [[False] * self.cols for _ in range(self.rows)]
        self.counts = [[0] * self.cols for _ in range(self.rows)]
        self.first_click = True
        self.game_over = False
        self.won = False
        self.recorded = False  # has this game's result been written to stats yet
        self.exploded = None  # (r, c) of mine that ended the game

    def place_mines(self, safe_r, safe_c):
        safe = {(safe_r + dr, safe_c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
        candidates = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in safe]
        self.mines = set(random.sample(candidates, self.mines_count))
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mines:
                    self.counts[r][c] = -1
                else:
                    self.counts[r][c] = sum(
                        ((r + dr, c + dc) in self.mines)
                        for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                        if not (dr == 0 and dc == 0)
                    )

    def neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc

    def reveal(self, r, c):
        if self.game_over or self.flagged[r][c] or self.revealed[r][c]:
            return
        if self.first_click:
            self.place_mines(r, c)
            self.first_click = False
        if (r, c) in self.mines:
            self.revealed[r][c] = True
            self.exploded = (r, c)
            self.game_over = True
            return
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if self.revealed[cr][cc] or self.flagged[cr][cc]:
                continue
            self.revealed[cr][cc] = True
            if self.counts[cr][cc] == 0:
                for nr, nc in self.neighbors(cr, cc):
                    if not self.revealed[nr][nc]:
                        stack.append((nr, nc))
        self.check_win()

    def chord(self, r, c):
        """Double-click on a revealed number: if flag count around it matches
        the number, reveal all non-flagged neighbors. Wrong flags = boom."""
        if self.game_over or not self.revealed[r][c] or self.counts[r][c] <= 0:
            return
        flag_count = sum(self.flagged[nr][nc] for nr, nc in self.neighbors(r, c))
        if flag_count != self.counts[r][c]:
            return
        for nr, nc in self.neighbors(r, c):
            if not self.flagged[nr][nc] and not self.revealed[nr][nc]:
                self.reveal(nr, nc)
                if self.game_over and not self.won:
                    return

    def toggle_flag(self, r, c):
        if self.game_over or self.revealed[r][c]:
            return
        self.flagged[r][c] = not self.flagged[r][c]

    def check_win(self):
        revealed_count = sum(self.revealed[r][c] for r in range(self.rows) for c in range(self.cols))
        if revealed_count == self.rows * self.cols - self.mines_count:
            self.won = True
            self.game_over = True

    def flag_count(self):
        return sum(self.flagged[r][c] for r in range(self.rows) for c in range(self.cols))


def draw_hidden(screen, rect, hover):
    top = HIDDEN_HOVER if hover else HIDDEN_TOP
    for i in range(rect.height):
        t = i / max(1, rect.height - 1)
        col = (
            int(top[0] * (1 - t) + HIDDEN_BOT[0] * t),
            int(top[1] * (1 - t) + HIDDEN_BOT[1] * t),
            int(top[2] * (1 - t) + HIDDEN_BOT[2] * t),
        )
        pygame.draw.line(screen, col, (rect.x, rect.y + i), (rect.right - 1, rect.y + i))
    pygame.draw.rect(screen, (30, 32, 40), rect, 1)


def draw_flag(screen, rect):
    pole_x = rect.x + rect.width // 3
    pygame.draw.line(screen, FLAG_POLE, (pole_x, rect.y + 5), (pole_x, rect.bottom - 5), 2)
    pygame.draw.polygon(screen, FLAG_RED, [
        (pole_x, rect.y + 5),
        (rect.right - 6, rect.y + rect.height // 3),
        (pole_x, rect.y + rect.height // 2 + 1),
    ])
    pygame.draw.rect(screen, FLAG_POLE, (pole_x - 4, rect.bottom - 8, 10, 3))


def draw_mine(screen, rect, exploded=False):
    cx, cy = rect.center
    r = rect.width // 3
    if exploded:
        pygame.draw.circle(screen, BOOM, (cx, cy), r + 3)
    pygame.draw.circle(screen, MINE_BLACK, (cx, cy), r)
    for dx, dy in [(-r-2, 0), (r+2, 0), (0, -r-2), (0, r+2)]:
        pygame.draw.line(screen, MINE_BLACK, (cx, cy), (cx + dx, cy + dy), 2)
    pygame.draw.circle(screen, MINE_SHINE, (cx - r // 3, cy - r // 3), max(2, r // 5))


def difficulty_button_rects(W):
    """Return ordered list of (name, rect) for the B/I/E selector pills."""
    rects = []
    btn_w, btn_h = 28, 24
    gap = 6
    total = len(DIFFICULTIES) * btn_w + (len(DIFFICULTIES) - 1) * gap
    x0 = (W - total) // 2
    y0 = 12
    for i, name in enumerate(DIFFICULTIES):
        rects.append((name, pygame.Rect(x0 + i * (btn_w + gap), y0, btn_w, btn_h)))
    return rects


def draw(screen, board, font, big_font, mono, hover_cell, W, H, difficulty, stats):
    screen.fill(BG)

    header = pygame.Rect(0, 0, W, MARGIN_TOP)
    pygame.draw.rect(screen, PANEL, header)
    pygame.draw.line(screen, (60, 64, 76), (0, MARGIN_TOP - 1), (W, MARGIN_TOP - 1))

    remaining = board.mines_count - board.flag_count()
    if board.won:
        status_text, status_color = "YOU WIN", ACCENT_OK
    elif board.game_over:
        status_text, status_color = "GAME OVER", ACCENT_BAD
    else:
        status_text, status_color = "MINESWEEPER", TEXT

    title = big_font.render(status_text, True, status_color)
    screen.blit(title, (PAD, 14))

    for name, rect in difficulty_button_rects(W):
        selected = (name == difficulty)
        bg = ACCENT_SEL if selected else (20, 22, 28)
        pygame.draw.rect(screen, bg, rect, border_radius=5)
        label = mono.render(DIFFICULTIES[name]["label"], True, TEXT)
        screen.blit(label, label.get_rect(center=rect.center))

    counter = mono.render(f"{remaining:03d}", True, FLAG_RED)
    counter_w = counter.get_width() + 22
    counter_rect = pygame.Rect(W - counter_w - PAD, 14, counter_w, 30)
    pygame.draw.rect(screen, (20, 22, 28), counter_rect, border_radius=6)
    screen.blit(counter, counter.get_rect(center=counter_rect.center))

    s = stats[difficulty]
    wl_surf = font.render(f"{difficulty}  W {s['wins']}  L {s['losses']}  (S for stats)", True, SUBTEXT)
    wl_rect = wl_surf.get_rect(topleft=(PAD, MARGIN_TOP - wl_surf.get_height() - 22))
    screen.blit(wl_surf, wl_rect.topleft)

    hint = font.render("L-click reveal · R-click flag · Double-click chord · R reset · B/I/E difficulty", True, SUBTEXT)
    screen.blit(hint, (PAD, MARGIN_TOP - hint.get_height() - 6))
    return wl_rect

    grid_rect = pygame.Rect(PAD - 2, MARGIN_TOP - 2, board.cols * CELL + 4, board.rows * CELL + 4)
    pygame.draw.rect(screen, GRID_LINE, grid_rect, border_radius=4)

    for r in range(board.rows):
        for c in range(board.cols):
            x = PAD + c * CELL
            y = MARGIN_TOP + r * CELL
            rect = pygame.Rect(x, y, CELL, CELL)
            if board.revealed[r][c]:
                base = REVEALED if (r + c) % 2 == 0 else REVEALED_ALT
                pygame.draw.rect(screen, base, rect)
                pygame.draw.rect(screen, (170, 174, 184), rect, 1)
                if (r, c) in board.mines:
                    draw_mine(screen, rect, exploded=(board.exploded == (r, c)))
                elif board.counts[r][c] > 0:
                    n = board.counts[r][c]
                    t = big_font.render(str(n), True, NUM_COLORS.get(n, (0, 0, 0)))
                    screen.blit(t, t.get_rect(center=rect.center))
            else:
                draw_hidden(screen, rect, hover=(hover_cell == (r, c)))
                if board.flagged[r][c]:
                    draw_flag(screen, rect)

    if board.game_over and not board.won:
        for (mr, mc) in board.mines:
            if not board.revealed[mr][mc]:
                x = PAD + mc * CELL
                y = MARGIN_TOP + mr * CELL
                rect = pygame.Rect(x, y, CELL, CELL)
                pygame.draw.rect(screen, REVEALED, rect)
                pygame.draw.rect(screen, (170, 174, 184), rect, 1)
                if board.flagged[mr][mc]:
                    draw_flag(screen, rect)
                else:
                    draw_mine(screen, rect)
        for r in range(board.rows):
            for c in range(board.cols):
                if board.flagged[r][c] and (r, c) not in board.mines:
                    x = PAD + c * CELL
                    y = MARGIN_TOP + r * CELL
                    rect = pygame.Rect(x, y, CELL, CELL)
                    pygame.draw.rect(screen, REVEALED, rect)
                    pygame.draw.rect(screen, (170, 174, 184), rect, 1)
                    draw_flag(screen, rect)
                    pygame.draw.line(screen, ACCENT_BAD, rect.topleft, rect.bottomright, 3)
                    pygame.draw.line(screen, ACCENT_BAD, rect.topright, rect.bottomleft, 3)


def draw_stats_overlay(screen, font, big_font, mono, W, H, stats):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    pad = 18
    line_h = 28
    rows = len(DIFFICULTIES) + 2  # title + header + rows
    panel_w = min(420, W - 40)
    panel_h = pad * 2 + line_h * rows
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GRID_LINE, panel, 1, border_radius=8)

    title = big_font.render("STATS", True, TEXT)
    screen.blit(title, (panel.x + pad, panel.y + pad))

    col_x = [panel.x + pad, panel.x + pad + 160, panel.x + pad + 230, panel.x + pad + 290, panel.x + pad + 350]
    y = panel.y + pad + line_h
    header = [("Difficulty", TEXT), ("W", ACCENT_OK), ("L", ACCENT_BAD), ("%", SUBTEXT)]
    for i, (h, col) in enumerate(header):
        screen.blit(mono.render(h, True, col), (col_x[i], y))
    y += line_h

    for name in DIFFICULTIES:
        s = stats[name]
        total = s["wins"] + s["losses"]
        pct = f"{(s['wins'] * 100 // total)}%" if total else "—"
        cells = [name, str(s["wins"]), str(s["losses"]), pct]
        for i, txt in enumerate(cells):
            screen.blit(font.render(txt, True, TEXT), (col_x[i], y + 4))
        y += line_h

    hint = font.render("S or click to close", True, SUBTEXT)
    screen.blit(hint, (panel.right - hint.get_width() - pad, panel.bottom - hint.get_height() - 8))


def cell_at(pos, board):
    mx, my = pos
    if my < MARGIN_TOP or mx < PAD or mx >= PAD + board.cols * CELL or my >= MARGIN_TOP + board.rows * CELL:
        return None
    return ((my - MARGIN_TOP) // CELL, (mx - PAD) // CELL)


def window_size(rows, cols):
    return (cols * CELL + PAD * 2, rows * CELL + MARGIN_TOP + PAD)


def make_board(name):
    d = DIFFICULTIES[name]
    return Board(d["rows"], d["cols"], d["mines"])


def main():
    pygame.init()
    pygame.display.set_caption("Minesweeper")

    stats = load_stats()
    difficulty = DEFAULT_DIFFICULTY
    board = make_board(difficulty)
    W, H = window_size(board.rows, board.cols)
    screen = pygame.display.set_mode((W, H))

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 13)
    big_font = pygame.font.SysFont("Segoe UI", 20, bold=True)
    mono = pygame.font.SysFont("Consolas", 16, bold=True)

    last_click_time = 0
    last_click_cell = None
    show_stats = False
    wl_rect = pygame.Rect(0, 0, 0, 0)

    def switch_difficulty(new_name):
        nonlocal board, difficulty, W, H, screen, last_click_cell
        if new_name == difficulty:
            board.reset()
            return
        difficulty = new_name
        board = make_board(difficulty)
        W, H = window_size(board.rows, board.cols)
        screen = pygame.display.set_mode((W, H))
        last_click_cell = None

    while True:
        hover = cell_at(pygame.mouse.get_pos(), board)

        if board.game_over and not board.recorded:
            key = "wins" if board.won else "losses"
            stats[difficulty][key] += 1
            save_stats(stats)
            board.recorded = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    show_stats = not show_stats
                elif event.key == pygame.K_r:
                    board.reset()
                else:
                    for name, d in DIFFICULTIES.items():
                        if event.key == d["key"]:
                            switch_difficulty(name)
                            break
            if event.type == pygame.MOUSEBUTTONDOWN:
                if show_stats and event.button == 1:
                    show_stats = False
                    continue
                if event.button == 1 and wl_rect.collidepoint(event.pos):
                    show_stats = True
                    continue
                if event.button == 1 and event.pos[1] < MARGIN_TOP:
                    clicked_btn = False
                    for name, rect in difficulty_button_rects(W):
                        if rect.collidepoint(event.pos):
                            switch_difficulty(name)
                            clicked_btn = True
                            break
                    if clicked_btn:
                        continue

                cell = cell_at(event.pos, board)
                if cell is None:
                    continue
                r, c = cell
                if event.button == 1:
                    now = pygame.time.get_ticks()
                    if last_click_cell == cell and now - last_click_time <= DOUBLE_CLICK_MS:
                        board.chord(r, c)
                        last_click_cell = None
                    else:
                        board.reveal(r, c)
                        last_click_cell = cell
                        last_click_time = now
                elif event.button == 3:
                    board.toggle_flag(r, c)

        wl_rect = draw(screen, board, font, big_font, mono, hover, W, H, difficulty, stats)
        if show_stats:
            draw_stats_overlay(screen, font, big_font, mono, W, H, stats)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
