"""Pinesweeper in pygame. Left-click reveals, right-click flags,
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
MARGIN_TOP = 96
PAD = 14
DOUBLE_CLICK_MS = 350

DIFFICULTIES = {
    "Beginner":     {"rows": 9,  "cols": 9,  "mines": 10, "key": pygame.K_b, "label": "B"},
    "Intermediate": {"rows": 16, "cols": 16, "mines": 40, "key": pygame.K_i, "label": "I"},
    "Expert":       {"rows": 16, "cols": 30, "mines": 99, "key": pygame.K_e, "label": "E"},
}
DEFAULT_DIFFICULTY = "Intermediate"
STATS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")

# palette - Windows 7 Minesweeper, tinted with the mint/cyan/evergreen set
#   aquamarine #b5ffe1  celadon #93e5ab  mint-leaf #65b891
#   dark-cyan  #4e878c  evergreen #00241b
AQUAMARINE = (181, 255, 225)
CELADON = (147, 229, 171)
MINT = (101, 184, 145)
DARK_CYAN = (78, 135, 140)
EVERGREEN = (0, 36, 27)

# Win7 chrome: light silvery field with raised/sunken bevels
BG = (222, 240, 232)           # frosted mint window bg
PANEL = (202, 226, 216)        # header/panel face
FIELD_BG = (198, 222, 212)     # play-field base
# hidden tile: classic raised button, tinted celadon
HIDDEN_TOP = (198, 236, 214)   # glossy top face
HIDDEN_BOT = (150, 205, 176)   # shaded bottom face
HIDDEN_HOVER_TOP = (214, 248, 228)
HIDDEN_HOVER_BOT = (170, 222, 194)
HIDDEN_EDGE_LIGHT = (235, 252, 244)  # top/left highlight
HIDDEN_EDGE_DARK = (96, 150, 124)    # bottom/right shadow
# revealed = recessed pale cell with thin grid seams
REVEALED = (224, 242, 234)
REVEALED_ALT = (214, 234, 225)
REVEALED_EDGE = (150, 190, 172)  # inset shadow on cleared tiles
GRID_LINE = (120, 170, 150)      # seams between tiles
BEVEL_LIGHT = (245, 255, 250)    # outer raised highlight
BEVEL_DARK = (110, 158, 138)     # outer raised shadow
TEXT = (18, 54, 42)
SUBTEXT = (78, 135, 140)         # dark-cyan
ACCENT_OK = (46, 150, 96)
ACCENT_BAD = (196, 72, 60)
ACCENT_SEL = (101, 184, 145)     # mint
PILL_BG = (176, 214, 196)
PILL_EDGE_LIGHT = (232, 250, 242)
PILL_EDGE_DARK = (120, 170, 150)
LED_BG = (6, 20, 15)             # near-black LED housing
LED_ON = (255, 64, 48)           # red 7-seg digits
LED_OFF = (40, 14, 12)           # unlit segment ghost
FLAG_RED = (200, 48, 48)
FLAG_POLE = (32, 44, 40)
PINE_DARK = (44, 92, 68)
PINE_MID = (78, 135, 140)        # dark-cyan
PINE_LIGHT = (147, 229, 171)     # celadon
PINE_SHADOW = (0, 36, 27)
BOOM = (255, 96, 72)
# numbers: classic Win minesweeper order, nudged toward the palette
NUM_COLORS = {
    1: (36, 96, 168),     # blue
    2: (30, 128, 84),     # green
    3: (196, 72, 60),     # red
    4: (60, 62, 140),     # navy
    5: (140, 48, 48),     # maroon
    6: (78, 135, 140),    # dark-cyan / teal
    7: (24, 54, 42),      # near-black evergreen
    8: (90, 110, 104),    # gray
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
    top = HIDDEN_HOVER_TOP if hover else HIDDEN_TOP
    bot = HIDDEN_HOVER_BOT if hover else HIDDEN_BOT
    for i in range(rect.height):
        t = i / max(1, rect.height - 1)
        col = (
            int(top[0] * (1 - t) + bot[0] * t),
            int(top[1] * (1 - t) + bot[1] * t),
            int(top[2] * (1 - t) + bot[2] * t),
        )
        pygame.draw.line(screen, col, (rect.x, rect.y + i), (rect.right - 1, rect.y + i))
    # classic Win7 raised button: 2px light on top/left, 2px dark on bottom/right
    for d in (0, 1):
        pygame.draw.line(screen, HIDDEN_EDGE_LIGHT, (rect.x + d, rect.y + d), (rect.right - 1 - d, rect.y + d))
        pygame.draw.line(screen, HIDDEN_EDGE_LIGHT, (rect.x + d, rect.y + d), (rect.x + d, rect.bottom - 1 - d))
        pygame.draw.line(screen, HIDDEN_EDGE_DARK, (rect.x + d, rect.bottom - 1 - d), (rect.right - 1 - d, rect.bottom - 1 - d))
        pygame.draw.line(screen, HIDDEN_EDGE_DARK, (rect.right - 1 - d, rect.y + d), (rect.right - 1 - d, rect.bottom - 1 - d))


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
    """Draw a pinecone in the cell. If exploded, flash a warm halo behind it."""
    cx, cy = rect.center
    w = rect.width
    if exploded:
        pygame.draw.circle(screen, BOOM, (cx, cy), w // 2 - 2)

    # body: ovoid built from overlapping scale rows (chevrons)
    body_w = int(w * 0.55)
    body_h = int(w * 0.72)
    top = cy - body_h // 2
    rows = 5
    row_h = body_h // rows
    for i in range(rows):
        # row gets narrower toward top and bottom (ovoid)
        taper = 1 - abs((i - (rows - 1) / 2) / ((rows - 1) / 2)) * 0.35
        rw = int(body_w * taper)
        ry = top + i * row_h
        # base scale
        pygame.draw.ellipse(screen, PINE_DARK, (cx - rw // 2, ry, rw, row_h + 2))
        # highlight chevron
        hl_w = max(2, rw - 6)
        pygame.draw.ellipse(screen, PINE_MID, (cx - hl_w // 2, ry + 1, hl_w, max(2, row_h - 1)))
        # tiny top edge highlight
        pygame.draw.arc(screen, PINE_LIGHT,
                        (cx - hl_w // 2, ry, hl_w, max(3, row_h)),
                        3.4, 6.0, 1)

    # stem at top
    stem_w = max(2, w // 10)
    pygame.draw.rect(screen, FLAG_POLE, (cx - stem_w // 2, top - 3, stem_w, 4))
    # small needle sprigs
    pygame.draw.line(screen, PINE_LIGHT, (cx - 1, top - 2), (cx - 5, top - 6), 1)
    pygame.draw.line(screen, PINE_LIGHT, (cx + 1, top - 2), (cx + 5, top - 6), 1)


def draw_bevel(screen, rect, raised=True, light=BEVEL_LIGHT, dark=BEVEL_DARK, width=2):
    """Draw a Win7-style 3D bevel border. raised=True -> light top/left."""
    a, b = (light, dark) if raised else (dark, light)
    for d in range(width):
        pygame.draw.line(screen, a, (rect.x + d, rect.y + d), (rect.right - 1 - d, rect.y + d))
        pygame.draw.line(screen, a, (rect.x + d, rect.y + d), (rect.x + d, rect.bottom - 1 - d))
        pygame.draw.line(screen, b, (rect.x + d, rect.bottom - 1 - d), (rect.right - 1 - d, rect.bottom - 1 - d))
        pygame.draw.line(screen, b, (rect.right - 1 - d, rect.y + d), (rect.right - 1 - d, rect.bottom - 1 - d))


# 7-segment layout: which segments light for each digit.
#   segs: a(top) b(top-r) c(bot-r) d(bot) e(bot-l) f(top-l) g(mid)
_SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcfgd",
    "-": "g", " ": "",
}


def draw_led_digit(screen, rect, ch):
    """Draw one red 7-seg digit inside rect on the LED housing."""
    on = _SEG.get(ch, "")
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    t = max(2, w // 6)          # segment thickness
    m = t                        # margin
    midy = y + h // 2
    def seg(name):
        return LED_ON if name in on else LED_OFF
    # horizontal segments: a (top), g (mid), d (bottom)
    pygame.draw.polygon(screen, seg("a"), [(x+m, y+m), (x+w-m, y+m), (x+w-m-t, y+m+t), (x+m+t, y+m+t)])
    pygame.draw.polygon(screen, seg("g"), [(x+m, midy), (x+m+t, midy-t//2), (x+w-m-t, midy-t//2), (x+w-m, midy), (x+w-m-t, midy+t//2), (x+m+t, midy+t//2)])
    pygame.draw.polygon(screen, seg("d"), [(x+m+t, y+h-m-t), (x+w-m-t, y+h-m-t), (x+w-m, y+h-m), (x+m, y+h-m)])
    # vertical segments: f (top-l), b (top-r), e (bot-l), c (bot-r)
    pygame.draw.polygon(screen, seg("f"), [(x+m, y+m), (x+m+t, y+m+t), (x+m+t, midy-t//2), (x+m, midy)])
    pygame.draw.polygon(screen, seg("b"), [(x+w-m, y+m), (x+w-m, midy), (x+w-m-t, midy-t//2), (x+w-m-t, y+m+t)])
    pygame.draw.polygon(screen, seg("e"), [(x+m, midy), (x+m+t, midy+t//2), (x+m+t, y+h-m-t), (x+m, y+h-m)])
    pygame.draw.polygon(screen, seg("c"), [(x+w-m, midy), (x+w-m, y+h-m), (x+w-m-t, y+h-m-t), (x+w-m-t, midy+t//2)])


def draw_led_counter(screen, rect, value):
    """Draw a 3-digit LED counter (Win7 red-on-black) for value in rect."""
    pygame.draw.rect(screen, LED_BG, rect)
    draw_bevel(screen, rect, raised=False, light=(150, 190, 172), dark=(20, 40, 32), width=1)
    text = f"{max(-99, min(999, value)):3d}".replace(" ", " ")
    if value < 0:
        text = f"-{min(99, -value):02d}"
    text = text[-3:].rjust(3)
    inner = rect.inflate(-8, -6)
    dw = inner.width // 3
    for i, ch in enumerate(text):
        dr = pygame.Rect(inner.x + i * dw, inner.y, dw, inner.height)
        draw_led_digit(screen, dr, ch)


def difficulty_button_rects(W):
    """Return ordered list of (name, rect) for the B/I/E selector pills,
    centered in the Win7 control strip."""
    rects = []
    btn_w, btn_h = 34, 30
    gap = 8
    total = len(DIFFICULTIES) * btn_w + (len(DIFFICULTIES) - 1) * gap
    x0 = (W - total) // 2
    y0 = 46
    for i, name in enumerate(DIFFICULTIES):
        rects.append((name, pygame.Rect(x0 + i * (btn_w + gap), y0, btn_w, btn_h)))
    return rects


def draw(screen, board, font, big_font, mono, hover_cell, W, H, difficulty, stats):
    screen.fill(BG)

    # --- Win7 header: title bar + raised control strip ---
    header = pygame.Rect(0, 0, W, MARGIN_TOP)
    pygame.draw.rect(screen, PANEL, header)

    remaining = board.mines_count - board.flag_count()
    if board.won:
        status_text, status_color = "YOU WIN", ACCENT_OK
    elif board.game_over:
        status_text, status_color = "GAME OVER", ACCENT_BAD
    else:
        status_text, status_color = "PINESWEEPER", TEXT

    title = big_font.render(status_text, True, status_color)
    screen.blit(title, (PAD, 12))

    # raised control strip holding the two LED counters + difficulty buttons
    strip = pygame.Rect(PAD, 40, W - PAD * 2, 42)
    pygame.draw.rect(screen, PANEL, strip)
    draw_bevel(screen, strip, raised=True, width=2)

    # left LED: mines remaining
    led_w, led_h = 62, 30
    left_led = pygame.Rect(strip.x + 8, strip.y + (strip.height - led_h) // 2, led_w, led_h)
    draw_led_counter(screen, left_led, remaining)

    # right LED: doubles as W-L via total; show wins count Win7-style
    s = stats[difficulty]
    right_led = pygame.Rect(strip.right - led_w - 8, strip.y + (strip.height - led_h) // 2, led_w, led_h)
    draw_led_counter(screen, right_led, s["wins"])

    for name, rect in difficulty_button_rects(W):
        selected = (name == difficulty)
        face = ACCENT_SEL if selected else PILL_BG
        pygame.draw.rect(screen, face, rect)
        draw_bevel(screen, rect, raised=not selected,
                   light=PILL_EDGE_LIGHT, dark=PILL_EDGE_DARK, width=2)
        label = mono.render(DIFFICULTIES[name]["label"], True, EVERGREEN if selected else TEXT)
        screen.blit(label, label.get_rect(center=rect.center))

    # win/loss line (click target for stats overlay), sits under the strip
    wl_surf = font.render(f"{difficulty}   W {s['wins']}  ·  L {s['losses']}   (S for stats)", True, SUBTEXT)
    wl_rect = wl_surf.get_rect(topleft=(PAD, strip.bottom + 4))
    screen.blit(wl_surf, wl_rect.topleft)

    # sunken play-field frame
    grid_rect = pygame.Rect(PAD - 3, MARGIN_TOP - 3, board.cols * CELL + 6, board.rows * CELL + 6)
    pygame.draw.rect(screen, FIELD_BG, grid_rect)
    draw_bevel(screen, grid_rect, raised=False, width=2)

    for r in range(board.rows):
        for c in range(board.cols):
            x = PAD + c * CELL
            y = MARGIN_TOP + r * CELL
            rect = pygame.Rect(x, y, CELL, CELL)
            if board.revealed[r][c]:
                base = REVEALED if (r + c) % 2 == 0 else REVEALED_ALT
                pygame.draw.rect(screen, base, rect)
                # soft inset shadow along top/left so cleared tiles feel sunken
                pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.right - 1, rect.y))
                pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.x, rect.bottom - 1))
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
                pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.right - 1, rect.y))
                pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.x, rect.bottom - 1))
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
                    pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.right - 1, rect.y))
                    pygame.draw.line(screen, REVEALED_EDGE, rect.topleft, (rect.x, rect.bottom - 1))
                    draw_flag(screen, rect)
                    pygame.draw.line(screen, ACCENT_BAD, rect.topleft, rect.bottomright, 3)
                    pygame.draw.line(screen, ACCENT_BAD, rect.topright, rect.bottomleft, 3)

    return wl_rect


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
    pygame.display.set_caption("Pinesweeper")

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
