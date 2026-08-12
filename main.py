"""Pinesweeper in pygame. Left-click reveals, right-click flags,
double-click a number to chord-reveal neighbors.

Difficulties: B = Beginner (9x9, 10), I = Intermediate (16x16, 40),
E = Expert (16x30, 99). Press B/I/E to switch (also resets). Press R or F2 to
reset current difficulty. Wins/losses/best-times are persisted per-difficulty,
and the chosen theme in stats.json next to this file. Menu bar: Game / Options /
Help. Left LED is the game timer, right LED is mines remaining."""
import json
import os
import sys
import random
import pygame

CELL = 32
MENUBAR_H = 24
MARGIN_TOP = 96 + MENUBAR_H
PAD = 14
DOUBLE_CLICK_MS = 350

DIFFICULTIES = {
    "Beginner":     {"rows": 9,  "cols": 9,  "mines": 10, "key": pygame.K_b, "label": "B"},
    "Intermediate": {"rows": 16, "cols": 16, "mines": 40, "key": pygame.K_i, "label": "I"},
    "Expert":       {"rows": 16, "cols": 30, "mines": 99, "key": pygame.K_e, "label": "E"},
}
DEFAULT_DIFFICULTY = "Intermediate"
# When frozen by PyInstaller, __file__ lives in a temp extraction dir that is
# wiped on exit; write stats next to the executable instead so they persist.
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(_APP_DIR, "stats.json")

# top menu bar. Each item is (text, action). A separator is (None, None).
# An item whose action is ("submenu", [items...]) opens a flyout to the right.
# Difficulty/theme actions are built dynamically so they can be radio-checked.
def build_menus():
    theme_items = [(name, f"theme:{name}") for name in THEMES]
    return [
        ("Game", [
            ("New Game", "new"),
            ("High Scores", "stats"),
            (None, None),
            ("Beginner", "diff:Beginner"),
            ("Intermediate", "diff:Intermediate"),
            ("Expert", "diff:Expert"),
            (None, None),
            ("Exit", "exit"),
        ]),
        ("Options", [
            ("Theme", ("submenu", theme_items)),
        ]),
        ("Help", [
            ("Keyboard Shortcuts", "shortcuts"),
            ("About", "about"),
        ]),
    ]

# shortcut hints shown right-aligned in dropdown rows, keyed by action.
SHORTCUT_HINTS = {
    "new": "F2",
    "diff:Beginner": "B",
    "diff:Intermediate": "I",
    "diff:Expert": "E",
    "shortcuts": "",
    "stats": "S",
}
MENU_ITEM_H = 24
MENU_PAD_X = 12
MENU_HINT_GAP = 28  # space reserved for the right-aligned shortcut / arrow

# ---------------------------------------------------------------------------
# Themes. Each theme is a full palette; apply_theme() pushes the chosen one into
# module globals so every draw function keeps using the bare color names (BG,
# PANEL, ...). "Pine" is the original palette verbatim.
# ---------------------------------------------------------------------------
THEMES = {
    "Pine": {
        "BG": (222, 240, 232), "PANEL": (202, 226, 216),
        "MENUBAR_BG": (212, 232, 222), "MENU_HOVER": (147, 229, 171),
        "MENU_DROP_BG": (232, 246, 240), "MENU_SEP": (150, 190, 172),
        "FIELD_BG": (198, 222, 212),
        "HIDDEN_TOP": (198, 236, 214), "HIDDEN_BOT": (150, 205, 176),
        "HIDDEN_HOVER_TOP": (214, 248, 228), "HIDDEN_HOVER_BOT": (170, 222, 194),
        "HIDDEN_EDGE_LIGHT": (235, 252, 244), "HIDDEN_EDGE_DARK": (96, 150, 124),
        "GLOSS": (255, 255, 255),
        "REVEALED": (224, 242, 234), "REVEALED_ALT": (214, 234, 225),
        "REVEALED_EDGE": (150, 190, 172), "GRID_LINE": (170, 205, 190),
        "BEVEL_LIGHT": (245, 255, 250), "BEVEL_DARK": (110, 158, 138),
        "TEXT": (18, 54, 42), "SUBTEXT": (78, 135, 140),
        "MENU_TEXT": (12, 40, 28),
        "ACCENT_OK": (46, 150, 96), "ACCENT_BAD": (196, 72, 60),
        "ACCENT_SEL": (101, 184, 145),
        "LED_BG": (6, 20, 15), "LED_ON": (255, 64, 48), "LED_OFF": (40, 14, 12),
        "FLAG_RED": (200, 48, 48), "FLAG_POLE": (32, 44, 40),
        "PINE_DARK": (44, 92, 68), "PINE_MID": (78, 135, 140),
        "PINE_LIGHT": (147, 229, 171), "PINE_SHADOW": (0, 36, 27),
        "BOOM": (255, 96, 72),
        "FACE_BG": (238, 226, 120), "FACE_LINE": (60, 48, 12),
        "NUM_COLORS": {
            1: (36, 96, 168), 2: (30, 128, 84), 3: (196, 72, 60),
            4: (60, 62, 140), 5: (140, 48, 48), 6: (78, 135, 140),
            7: (24, 54, 42), 8: (90, 110, 104),
        },
    },
    "Classic": {
        "BG": (198, 198, 198), "PANEL": (192, 192, 192),
        "MENUBAR_BG": (208, 208, 208), "MENU_HOVER": (49, 106, 197),
        "MENU_DROP_BG": (240, 240, 240), "MENU_SEP": (150, 150, 150),
        "FIELD_BG": (189, 189, 189),
        "HIDDEN_TOP": (222, 222, 222), "HIDDEN_BOT": (168, 168, 168),
        "HIDDEN_HOVER_TOP": (236, 236, 236), "HIDDEN_HOVER_BOT": (186, 186, 186),
        "HIDDEN_EDGE_LIGHT": (255, 255, 255), "HIDDEN_EDGE_DARK": (128, 128, 128),
        "GLOSS": (255, 255, 255),
        "REVEALED": (208, 208, 208), "REVEALED_ALT": (200, 200, 200),
        "REVEALED_EDGE": (150, 150, 150), "GRID_LINE": (160, 160, 160),
        "BEVEL_LIGHT": (255, 255, 255), "BEVEL_DARK": (128, 128, 128),
        "TEXT": (24, 24, 24), "SUBTEXT": (90, 90, 90),
        "MENU_TEXT": (16, 16, 16),
        "ACCENT_OK": (0, 128, 0), "ACCENT_BAD": (200, 0, 0),
        "ACCENT_SEL": (49, 106, 197),
        "LED_BG": (0, 0, 0), "LED_ON": (255, 0, 0), "LED_OFF": (48, 0, 0),
        "FLAG_RED": (208, 0, 0), "FLAG_POLE": (0, 0, 0),
        "PINE_DARK": (40, 40, 40), "PINE_MID": (90, 90, 90),
        "PINE_LIGHT": (160, 160, 160), "PINE_SHADOW": (0, 0, 0),
        "BOOM": (255, 40, 40),
        "FACE_BG": (255, 224, 0), "FACE_LINE": (40, 40, 0),
        "NUM_COLORS": {
            1: (0, 0, 255), 2: (0, 128, 0), 3: (255, 0, 0),
            4: (0, 0, 128), 5: (128, 0, 0), 6: (0, 128, 128),
            7: (0, 0, 0), 8: (128, 128, 128),
        },
    },
    "Dark": {
        "BG": (30, 34, 38), "PANEL": (44, 50, 56),
        "MENUBAR_BG": (38, 43, 48), "MENU_HOVER": (70, 110, 90),
        "MENU_DROP_BG": (52, 58, 64), "MENU_SEP": (80, 88, 96),
        "FIELD_BG": (36, 41, 46),
        "HIDDEN_TOP": (72, 82, 92), "HIDDEN_BOT": (48, 55, 62),
        "HIDDEN_HOVER_TOP": (88, 100, 112), "HIDDEN_HOVER_BOT": (60, 70, 80),
        "HIDDEN_EDGE_LIGHT": (100, 114, 128), "HIDDEN_EDGE_DARK": (28, 32, 36),
        "GLOSS": (200, 220, 235),
        "REVEALED": (46, 52, 58), "REVEALED_ALT": (42, 48, 54),
        "REVEALED_EDGE": (28, 32, 36), "GRID_LINE": (58, 66, 74),
        "BEVEL_LIGHT": (96, 108, 120), "BEVEL_DARK": (24, 28, 32),
        "TEXT": (222, 232, 240), "SUBTEXT": (140, 158, 170),
        "MENU_TEXT": (236, 244, 250),
        "ACCENT_OK": (96, 210, 140), "ACCENT_BAD": (240, 110, 96),
        "ACCENT_SEL": (96, 200, 150),
        "LED_BG": (0, 0, 0), "LED_ON": (255, 72, 56), "LED_OFF": (48, 16, 14),
        "FLAG_RED": (232, 96, 88), "FLAG_POLE": (200, 210, 220),
        "PINE_DARK": (70, 130, 100), "PINE_MID": (110, 180, 150),
        "PINE_LIGHT": (170, 230, 200), "PINE_SHADOW": (10, 20, 16),
        "BOOM": (255, 120, 96),
        "FACE_BG": (232, 200, 80), "FACE_LINE": (30, 26, 8),
        "NUM_COLORS": {
            1: (110, 160, 250), 2: (110, 210, 140), 3: (240, 120, 110),
            4: (150, 150, 240), 5: (220, 130, 120), 6: (120, 200, 200),
            7: (220, 232, 240), 8: (170, 180, 190),
        },
    },
    # midnight-violet #160f29 / stormy-teal #246a73 / dark-cyan #368f8b
    # champagne-mist #f3dfc1 / desert-sand #ddbea8
    "Coastal": {
        "BG": (243, 223, 193), "PANEL": (221, 190, 168),
        "MENUBAR_BG": (233, 208, 182), "MENU_HOVER": (54, 143, 139),
        "MENU_DROP_BG": (247, 233, 210), "MENU_SEP": (190, 160, 140),
        "FIELD_BG": (221, 190, 168),
        "HIDDEN_TOP": (238, 214, 188), "HIDDEN_BOT": (206, 176, 152),
        "HIDDEN_HOVER_TOP": (248, 228, 204), "HIDDEN_HOVER_BOT": (220, 192, 168),
        "HIDDEN_EDGE_LIGHT": (252, 240, 222), "HIDDEN_EDGE_DARK": (150, 120, 100),
        "GLOSS": (255, 250, 240),
        "REVEALED": (243, 227, 204), "REVEALED_ALT": (236, 218, 194),
        "REVEALED_EDGE": (190, 160, 138), "GRID_LINE": (206, 178, 156),
        "BEVEL_LIGHT": (252, 242, 226), "BEVEL_DARK": (150, 122, 104),
        "TEXT": (22, 15, 41), "SUBTEXT": (36, 106, 115),
        "MENU_TEXT": (18, 12, 34),
        "ACCENT_OK": (54, 143, 139), "ACCENT_BAD": (176, 66, 54),
        "ACCENT_SEL": (36, 106, 115),
        "LED_BG": (22, 15, 41), "LED_ON": (255, 96, 72), "LED_OFF": (48, 24, 30),
        "FLAG_RED": (176, 66, 54), "FLAG_POLE": (22, 15, 41),
        "PINE_DARK": (36, 106, 115), "PINE_MID": (54, 143, 139),
        "PINE_LIGHT": (200, 224, 210), "PINE_SHADOW": (22, 15, 41),
        "BOOM": (255, 120, 90),
        "FACE_BG": (243, 223, 193), "FACE_LINE": (22, 15, 41),
        "NUM_COLORS": {
            1: (36, 106, 115), 2: (46, 125, 90), 3: (176, 66, 54),
            4: (54, 45, 110), 5: (150, 70, 60), 6: (54, 143, 139),
            7: (22, 15, 41), 8: (120, 100, 90),
        },
    },
    # prussian-blue #0a1128 / deep-navy #001f54 / yale-blue #034078
    # cerulean #1282a2 / white #fefcfb
    "Deep Ocean": {
        "BG": (10, 17, 40), "PANEL": (0, 31, 84),
        "MENUBAR_BG": (6, 24, 62), "MENU_HOVER": (18, 130, 162),
        "MENU_DROP_BG": (3, 40, 92), "MENU_SEP": (18, 130, 162),
        "FIELD_BG": (0, 24, 66),
        "HIDDEN_TOP": (3, 64, 120), "HIDDEN_BOT": (0, 31, 84),
        "HIDDEN_HOVER_TOP": (10, 84, 148), "HIDDEN_HOVER_BOT": (3, 45, 100),
        "HIDDEN_EDGE_LIGHT": (18, 130, 162), "HIDDEN_EDGE_DARK": (6, 16, 40),
        "GLOSS": (200, 230, 245),
        "REVEALED": (5, 34, 80), "REVEALED_ALT": (3, 29, 72),
        "REVEALED_EDGE": (6, 16, 40), "GRID_LINE": (14, 54, 104),
        "BEVEL_LIGHT": (18, 130, 162), "BEVEL_DARK": (6, 14, 34),
        "TEXT": (254, 252, 251), "SUBTEXT": (120, 180, 205),
        "MENU_TEXT": (255, 255, 255),
        "ACCENT_OK": (90, 200, 170), "ACCENT_BAD": (240, 110, 96),
        "ACCENT_SEL": (18, 130, 162),
        "LED_BG": (4, 10, 26), "LED_ON": (255, 80, 64), "LED_OFF": (44, 14, 12),
        "FLAG_RED": (240, 96, 88), "FLAG_POLE": (254, 252, 251),
        "PINE_DARK": (3, 64, 120), "PINE_MID": (18, 130, 162),
        "PINE_LIGHT": (170, 220, 235), "PINE_SHADOW": (4, 10, 26),
        "BOOM": (255, 110, 90),
        "FACE_BG": (240, 214, 90), "FACE_LINE": (10, 17, 40),
        "NUM_COLORS": {
            1: (90, 170, 240), 2: (90, 210, 160), 3: (240, 120, 110),
            4: (140, 150, 240), 5: (230, 140, 120), 6: (18, 180, 200),
            7: (254, 252, 251), 8: (160, 180, 200),
        },
    },
}


def apply_theme(name):
    """Copy the chosen palette into module globals so all draw functions using
    bare color names (BG, PANEL, NUM_COLORS, ...) pick it up."""
    if name not in THEMES:
        name = "Pine"
    globals().update(THEMES[name])
    globals()["CURRENT_THEME"] = name


# initialize globals to the default palette at import time
apply_theme("Pine")


def load_state():
    """Load per-difficulty wins/losses/best_time plus settings (theme).
    Returns (stats, settings). Back-compat with old wins/losses-only files."""
    stats = {name: {"wins": 0, "losses": 0, "best_time": None, "scores": []} for name in DIFFICULTIES}
    settings = {"theme": "Pine"}
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for name in DIFFICULTIES:
            if isinstance(data.get(name), dict):
                stats[name]["wins"] = int(data[name].get("wins", 0))
                stats[name]["losses"] = int(data[name].get("losses", 0))
                bt = data[name].get("best_time", None)
                stats[name]["best_time"] = float(bt) if bt is not None else None
                raw = data[name].get("scores", [])
                scores = []
                if isinstance(raw, list):
                    for e in raw:
                        if isinstance(e, dict) and "time" in e:
                            try:
                                nm = str(e.get("name", "AAA")).upper()[:3].ljust(3)
                                scores.append({"name": nm, "time": float(e["time"])})
                            except (ValueError, TypeError):
                                pass
                scores.sort(key=lambda s: s["time"])
                stats[name]["scores"] = scores[:3]
        if isinstance(data.get("settings"), dict):
            t = data["settings"].get("theme", "Pine")
            settings["theme"] = t if t in THEMES else "Pine"
    except (FileNotFoundError, ValueError, OSError):
        pass
    return stats, settings


def save_state(stats, settings):
    try:
        out = {name: stats[name] for name in DIFFICULTIES}
        out["settings"] = settings
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
    except OSError:
        pass


def qualifies(scores, secs):
    """True if a win time of `secs` earns a spot in the top-3 list."""
    return len(scores) < 3 or secs < scores[-1]["time"]


def insert_score(scores, name, secs):
    """Insert (name, secs), keep sorted ascending by time, truncate to 3.
    Returns the rank (1-based) of the new entry, or None if it didn't place."""
    entry = {"name": name.upper()[:3].ljust(3), "time": round(float(secs), 1)}
    scores.append(entry)
    scores.sort(key=lambda s: s["time"])
    del scores[3:]
    return (scores.index(entry) + 1) if entry in scores else None


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

    def any_revealed(self):
        return any(self.revealed[r][c] for r in range(self.rows) for c in range(self.cols))


def draw_hidden(screen, rect, hover):
    """Glossy Win7-style raised tile: vertical base gradient + a bright diagonal
    sheen across the top-left, finished with a 2px raised bevel."""
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

    # glossy top highlight: a bright band over the upper ~48%, fading fast so it
    # reads as a crisp Aero sheen rather than a flat wash
    gloss = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    gh = int(rect.height * 0.48)
    for i in range(gh):
        t = i / max(1, gh)
        a = int(170 * (1 - t) ** 1.5)  # steep falloff downward
        pygame.draw.line(gloss, (GLOSS[0], GLOSS[1], GLOSS[2], a), (0, i), (rect.width - 1, i))
    screen.blit(gloss, rect.topleft)

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


def draw_bevel(screen, rect, raised=True, light=None, dark=None, width=2):
    """Draw a Win7-style 3D bevel border. raised=True -> light top/left."""
    if light is None:
        light = BEVEL_LIGHT
    if dark is None:
        dark = BEVEL_DARK
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
    text = f"{max(-99, min(999, value)):3d}"
    if value < 0:
        text = f"-{min(99, -value):02d}"
    text = text[-3:].rjust(3)
    inner = rect.inflate(-8, -6)
    dw = inner.width // 3
    for i, ch in enumerate(text):
        dr = pygame.Rect(inner.x + i * dw, inner.y, dw, inner.height)
        draw_led_digit(screen, dr, ch)


def draw_clock_icon(screen, cx, cy, r):
    """Small analog clock glyph left of the timer LED."""
    pygame.draw.circle(screen, SUBTEXT, (cx, cy), r)
    pygame.draw.circle(screen, LED_BG, (cx, cy), r - 2)
    pygame.draw.line(screen, LED_ON, (cx, cy), (cx, cy - (r - 4)), 2)          # minute hand up
    pygame.draw.line(screen, LED_ON, (cx, cy), (cx + (r - 5), cy), 2)          # hour hand right


# ---------------------------------------------------------------------------
# Menu bar
# ---------------------------------------------------------------------------
def menu_label_rects(font, menus):
    """Return ordered list of (label, items, rect) for the top-bar menu labels."""
    rects = []
    x = 2
    for label, items in menus:
        w = font.size(label)[0] + MENU_PAD_X * 2
        rects.append((label, items, pygame.Rect(x, 0, w, MENUBAR_H)))
        x += w
    return rects


def dropdown_rects(anchor_rect, items, font, below=True):
    """Compute a dropdown panel + its item rects. If below, panel drops from the
    bottom of anchor_rect (top-bar menu); otherwise it flies out to the right of
    anchor_rect (submenu). Returns (panel_rect, [(text, action, item_rect), ...])."""
    w = 0
    for text, action in items:
        if text is not None:
            hint = ""
            if isinstance(action, tuple) and action[0] == "submenu":
                hint = ">"
            else:
                hint = SHORTCUT_HINTS.get(action, "")
            extra = MENU_HINT_GAP if hint else 0
            w = max(w, font.size(text)[0] + extra)
    w += MENU_PAD_X * 2
    w = max(w, anchor_rect.width)
    if below:
        x, y = anchor_rect.x, anchor_rect.bottom
    else:
        x, y = anchor_rect.right - 2, anchor_rect.y
    item_rects = []
    cy = y + 4
    for text, action in items:
        h = 6 if text is None else MENU_ITEM_H
        item_rects.append((text, action, pygame.Rect(x, cy, w, h)))
        cy += h
    panel = pygame.Rect(x, y, w, cy - y + 4)
    return panel, item_rects


def _checked_action(action, difficulty, theme):
    """Return True if this action represents the currently-active radio choice."""
    if isinstance(action, str):
        if action == f"diff:{difficulty}":
            return True
        if action == f"theme:{theme}":
            return True
    return False


def draw_dropdown(screen, font, panel, item_rects, hover_item, difficulty, theme):
    pygame.draw.rect(screen, MENU_DROP_BG, panel)
    draw_bevel(screen, panel, raised=True, width=1)
    for text, action, irect in item_rects:
        if text is None:
            midy = irect.y + irect.height // 2
            pygame.draw.line(screen, MENU_SEP, (irect.x + 6, midy), (irect.right - 6, midy))
            continue
        hovered = (hover_item is not None and _same_action(action, hover_item))
        if hovered:
            pygame.draw.rect(screen, MENU_HOVER, irect)
        # radio check dot
        if _checked_action(action, difficulty, theme):
            dot = irect.y + irect.height // 2
            pygame.draw.circle(screen, TEXT, (irect.x + 6, dot), 3)
        t = font.render(text, True, TEXT)
        screen.blit(t, (irect.x + MENU_PAD_X, irect.y + (irect.height - t.get_height()) // 2))
        # right-aligned hint (submenu arrow or shortcut)
        if isinstance(action, tuple) and action[0] == "submenu":
            hint = ">"
        else:
            hint = SHORTCUT_HINTS.get(action, "")
        if hint:
            ht = font.render(hint, True, SUBTEXT)
            screen.blit(ht, (irect.right - ht.get_width() - 8,
                             irect.y + (irect.height - ht.get_height()) // 2))


def _same_action(a, b):
    """Compare actions where a submenu action is a tuple (unhashable to eq by id
    otherwise fine). Plain string actions compare by value."""
    if isinstance(a, tuple) and isinstance(b, tuple):
        return a[0] == b[0] and a[1] == b[1]
    return a == b


def draw_menubar(screen, font, W, open_menu, open_submenu, hover_item, menus, difficulty, theme):
    """Draw the menu bar, the open dropdown (if any), and an open submenu flyout."""
    bar = pygame.Rect(0, 0, W, MENUBAR_H)
    pygame.draw.rect(screen, MENUBAR_BG, bar)
    pygame.draw.line(screen, MENU_SEP, (0, MENUBAR_H - 1), (W, MENUBAR_H - 1))

    labels = menu_label_rects(font, menus)
    label_col = globals().get("MENU_TEXT", TEXT)
    for label, items, rect in labels:
        if label == open_menu:
            pygame.draw.rect(screen, MENU_HOVER, rect)
        t = font.render(label, True, label_col)
        screen.blit(t, t.get_rect(center=rect.center))

    if open_menu is None:
        return

    for label, items, rect in labels:
        if label != open_menu:
            continue
        panel, item_rects = dropdown_rects(rect, items, font, below=True)
        draw_dropdown(screen, font, panel, item_rects, hover_item, difficulty, theme)
        # submenu flyout
        if open_submenu is not None:
            for text, action, irect in item_rects:
                if isinstance(action, tuple) and action[0] == "submenu" and text == open_submenu:
                    sub_items = action[1]
                    spanel, sitem_rects = dropdown_rects(irect, sub_items, font, below=False)
                    draw_dropdown(screen, font, spanel, sitem_rects, hover_item, difficulty, theme)
                    break
        break


def hovered_menu_action(font, menus, open_menu, open_submenu, pos):
    """Return the action under `pos` within the open dropdown/submenu, or None."""
    if open_menu is None:
        return None
    labels = menu_label_rects(font, menus)
    for label, items, rect in labels:
        if label != open_menu:
            continue
        panel, item_rects = dropdown_rects(rect, items, font, below=True)
        # submenu takes priority (drawn on top)
        if open_submenu is not None:
            for text, action, irect in item_rects:
                if isinstance(action, tuple) and action[0] == "submenu" and text == open_submenu:
                    _, sitem_rects = dropdown_rects(irect, action[1], font, below=False)
                    for st, sa, srect in sitem_rects:
                        if st is not None and srect.collidepoint(pos):
                            return sa
                    break
        for text, action, irect in item_rects:
            if text is not None and irect.collidepoint(pos):
                return action
        break
    return None


def draw(screen, board, font, big_font, mono, hover_cell, W, H, difficulty, stats,
         elapsed):
    screen.fill(BG)

    # --- header: title bar + raised control strip ---
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
    screen.blit(title, (PAD, 12 + MENUBAR_H))

    # raised control strip holding the timer + mines LEDs
    strip = pygame.Rect(PAD, 40 + MENUBAR_H, W - PAD * 2, 42)
    pygame.draw.rect(screen, PANEL, strip)
    draw_bevel(screen, strip, raised=True, width=2)

    led_w, led_h = 62, 30
    # left LED: game timer, with a clock glyph to its left
    clock_r = 9
    clock_cx = strip.x + 8 + clock_r
    draw_clock_icon(screen, clock_cx, strip.centery, clock_r)
    left_led = pygame.Rect(clock_cx + clock_r + 6, strip.y + (strip.height - led_h) // 2, led_w, led_h)
    draw_led_counter(screen, left_led, int(elapsed))

    # right LED: mines remaining
    right_led = pygame.Rect(strip.right - led_w - 8, strip.y + (strip.height - led_h) // 2, led_w, led_h)
    draw_led_counter(screen, right_led, remaining)

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
                # thin light seams + soft inset shadow top/left
                pygame.draw.line(screen, GRID_LINE, (rect.right - 1, rect.y), (rect.right - 1, rect.bottom - 1))
                pygame.draw.line(screen, GRID_LINE, (rect.x, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
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


def _fmt_time(secs):
    if secs is None:
        return "\u2014"
    secs = int(secs)
    return f"{secs // 60}:{secs % 60:02d}"


def draw_scoreboard_overlay(screen, font, big_font, mono, W, H, stats):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    pad = 18
    line_h = 28
    score_h = 22
    # rows: title + header + one row per difficulty + a "TOP TIMES" section
    # (blank + heading + 3 lines per difficulty)
    table_rows = len(DIFFICULTIES) + 2
    top_lines = 1 + sum(1 + 3 for _ in DIFFICULTIES)  # heading + (label+3) each
    panel_w = min(480, W - 40)
    panel_h = pad * 2 + line_h * table_rows + line_h + top_lines * score_h + 8
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GRID_LINE, panel, 1, border_radius=8)

    title = big_font.render("SCOREBOARD", True, TEXT)
    screen.blit(title, (panel.x + pad, panel.y + pad))

    col_x = [panel.x + pad, panel.x + pad + 150, panel.x + pad + 215,
             panel.x + pad + 275, panel.x + pad + 340]
    y = panel.y + pad + line_h
    header = [("Difficulty", TEXT), ("W", ACCENT_OK), ("L", ACCENT_BAD),
              ("%", SUBTEXT), ("Best", SUBTEXT)]
    for i, (h, col) in enumerate(header):
        screen.blit(mono.render(h, True, col), (col_x[i], y))
    y += line_h

    for name in DIFFICULTIES:
        s = stats[name]
        total = s["wins"] + s["losses"]
        pct = f"{(s['wins'] * 100 // total)}%" if total else "\u2014"
        cells = [name, str(s["wins"]), str(s["losses"]), pct, _fmt_time(s.get("best_time"))]
        for i, txt in enumerate(cells):
            screen.blit(font.render(txt, True, TEXT), (col_x[i], y + 4))
        y += line_h

    # --- TOP TIMES section ---
    y += 6
    screen.blit(mono.render("TOP TIMES", True, ACCENT_SEL), (panel.x + pad, y))
    y += score_h
    medal = [ACCENT_OK, SUBTEXT, ACCENT_BAD]
    for name in DIFFICULTIES:
        screen.blit(font.render(name, True, TEXT), (panel.x + pad, y))
        y += score_h
        scores = stats[name].get("scores", [])
        if not scores:
            screen.blit(font.render("   \u2014 no scores yet \u2014", True, SUBTEXT),
                        (panel.x + pad + 12, y))
            y += score_h
            y += score_h * 2  # keep spacing consistent (3 slots reserved)
            continue
        for i in range(3):
            if i < len(scores):
                e = scores[i]
                rank = mono.render(f"#{i+1}", True, medal[i])
                nm = font.render(e["name"], True, TEXT)
                tm = font.render(_fmt_time(e["time"]), True, SUBTEXT)
                screen.blit(rank, (panel.x + pad + 12, y))
                screen.blit(nm, (panel.x + pad + 52, y))
                screen.blit(tm, (panel.x + pad + 120, y))
            y += score_h

    hint = font.render("S or click to close", True, SUBTEXT)
    screen.blit(hint, (panel.right - hint.get_width() - pad, panel.bottom - hint.get_height() - 8))


def draw_initials_overlay(screen, font, big_font, mono, W, H, difficulty, secs, initials, rank):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    panel_w = min(340, W - 40)
    panel_h = 210
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, ACCENT_OK, panel, 2, border_radius=8)

    title = big_font.render("NEW HIGH SCORE", True, ACCENT_OK)
    screen.blit(title, title.get_rect(centerx=panel.centerx, y=panel.y + 16))

    sub = font.render(f"{difficulty}  \u00b7  #{rank}  \u00b7  {_fmt_time(secs)}", True, SUBTEXT)
    screen.blit(sub, sub.get_rect(centerx=panel.centerx, y=panel.y + 48))

    # three character boxes
    box_w, box_h, gap = 48, 56, 14
    total = box_w * 3 + gap * 2
    bx = panel.centerx - total // 2
    by = panel.y + 82
    active = min(len(initials), 2)
    for i in range(3):
        r = pygame.Rect(bx + i * (box_w + gap), by, box_w, box_h)
        pygame.draw.rect(screen, FIELD_BG, r)
        draw_bevel(screen, r, raised=False, width=2)
        ch = initials[i] if i < len(initials) else ""
        if ch:
            g = big_font.render(ch, True, TEXT)
            screen.blit(g, g.get_rect(center=r.center))
        # caret under the active slot
        if i == active and len(initials) < 3:
            pygame.draw.line(screen, ACCENT_SEL, (r.x + 8, r.bottom - 8),
                             (r.right - 8, r.bottom - 8), 3)

    hint = font.render("A\u2013Z to type \u00b7 Enter to save", True, SUBTEXT)
    screen.blit(hint, hint.get_rect(centerx=panel.centerx, y=panel.bottom - 30))


def draw_about_overlay(screen, font, big_font, W, H):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    panel_w = min(360, W - 40)
    panel_h = 150
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GRID_LINE, panel, 1, border_radius=8)
    lines = [
        (big_font, "Pinesweeper", TEXT),
        (font, "A minesweeper in pygame.", SUBTEXT),
        (font, "Left-click reveals \u00b7 right-click flags", SUBTEXT),
        (font, "Double-click a number to chord.", SUBTEXT),
    ]
    y = panel.y + 16
    for f, text, col in lines:
        screen.blit(f.render(text, True, col), (panel.x + 18, y))
        y += f.get_height() + 8
    hint = font.render("click to close", True, SUBTEXT)
    screen.blit(hint, (panel.right - hint.get_width() - 14, panel.bottom - hint.get_height() - 8))


def draw_shortcuts_overlay(screen, font, big_font, W, H):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    rows = [
        ("Left click", "Reveal cell"),
        ("Right click", "Toggle flag"),
        ("Double click", "Chord (reveal neighbors)"),
        ("F2 / R", "New game"),
        ("B / I / E", "Beginner / Intermediate / Expert"),
        ("S", "Scoreboard"),
    ]
    pad = 18
    line_h = 26
    panel_w = min(400, W - 40)
    panel_h = pad * 2 + line_h * (len(rows) + 1)
    panel = pygame.Rect((W - panel_w) // 2, (H - panel_h) // 2, panel_w, panel_h)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GRID_LINE, panel, 1, border_radius=8)
    screen.blit(big_font.render("SHORTCUTS", True, TEXT), (panel.x + pad, panel.y + pad))
    y = panel.y + pad + line_h + 6
    for key, desc in rows:
        screen.blit(font.render(key, True, ACCENT_SEL), (panel.x + pad, y))
        screen.blit(font.render(desc, True, TEXT), (panel.x + pad + 120, y))
        y += line_h
    hint = font.render("click to close", True, SUBTEXT)
    screen.blit(hint, (panel.right - hint.get_width() - 14, panel.bottom - hint.get_height() - 8))


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


def _resource_path(rel):
    """Path to a bundled resource, whether run from source or a PyInstaller exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    pygame.init()
    pygame.display.set_caption("Pinesweeper")
    try:
        pygame.display.set_icon(pygame.image.load(_resource_path("icon.png")))
    except (pygame.error, FileNotFoundError):
        pass

    stats, settings = load_state()
    apply_theme(settings["theme"])
    menus = build_menus()

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
    show_scoreboard = False
    show_about = False
    show_shortcuts = False
    open_menu = None
    open_submenu = None
    entering_initials = False   # initials-capture overlay active
    initials = ""               # buffer for the 3-letter name
    pending_rank = 0            # provisional rank shown in the overlay

    # timer state
    start_ticks = None      # ms when the game timer started (first reveal)
    frozen_elapsed = 0.0    # elapsed seconds frozen at game over

    def close_overlays():
        nonlocal show_scoreboard, show_about, show_shortcuts, open_menu, open_submenu
        show_scoreboard = show_about = show_shortcuts = False
        open_menu = open_submenu = None

    def current_elapsed():
        if start_ticks is None:
            return 0.0
        if board.game_over:
            return frozen_elapsed
        return (pygame.time.get_ticks() - start_ticks) / 1000.0

    def new_game():
        nonlocal start_ticks, frozen_elapsed, last_click_cell
        board.reset()
        start_ticks = None
        frozen_elapsed = 0.0
        last_click_cell = None

    def switch_difficulty(new_name):
        nonlocal board, difficulty, W, H, screen, last_click_cell, start_ticks, frozen_elapsed
        difficulty = new_name
        board = make_board(difficulty)
        W, H = window_size(board.rows, board.cols)
        screen = pygame.display.set_mode((W, H))
        last_click_cell = None
        start_ticks = None
        frozen_elapsed = 0.0

    def do_action(action):
        nonlocal show_scoreboard, show_about, show_shortcuts, settings
        if action == "new":
            new_game()
        elif action == "exit":
            pygame.quit()
            sys.exit()
        elif action == "stats":
            show_scoreboard = True
        elif action == "about":
            show_about = True
        elif action == "shortcuts":
            show_shortcuts = True
        elif isinstance(action, str) and action.startswith("diff:"):
            switch_difficulty(action.split(":", 1)[1])
        elif isinstance(action, str) and action.startswith("theme:"):
            name = action.split(":", 1)[1]
            apply_theme(name)
            settings["theme"] = name
            save_state(stats, settings)

    while True:
        # start timer on first reveal
        if start_ticks is None and board.any_revealed() and not board.game_over:
            start_ticks = pygame.time.get_ticks()

        # freeze timer + record result once on game over
        if board.game_over and not board.recorded:
            frozen_elapsed = (pygame.time.get_ticks() - start_ticks) / 1000.0 if start_ticks else 0.0
            if board.won:
                stats[difficulty]["wins"] += 1
                bt = stats[difficulty].get("best_time")
                if bt is None or frozen_elapsed < bt:
                    stats[difficulty]["best_time"] = round(frozen_elapsed, 1)
                # prompt for initials if this time earns a top-3 slot
                scores = stats[difficulty].get("scores", [])
                if qualifies(scores, frozen_elapsed):
                    entering_initials = True
                    initials = ""
                    # provisional rank = where this time would land
                    pending_rank = sum(1 for s in scores if s["time"] <= frozen_elapsed) + 1
                    close_overlays()
            else:
                stats[difficulty]["losses"] += 1
            save_state(stats, settings)
            board.recorded = True

        hover = cell_at(pygame.mouse.get_pos(), board)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # initials capture takes over all keyboard input while active
            if entering_initials and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    name = (initials or "AAA").ljust(3, "A")[:3]
                    insert_score(stats[difficulty]["scores"], name, frozen_elapsed)
                    save_state(stats, settings)
                    entering_initials = False
                    initials = ""
                elif event.key == pygame.K_BACKSPACE:
                    initials = initials[:-1]
                elif pygame.K_a <= event.key <= pygame.K_z and len(initials) < 3:
                    initials += chr(event.key).upper()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    show_scoreboard = not show_scoreboard
                elif event.key in (pygame.K_r, pygame.K_F2):
                    new_game()
                else:
                    for name, d in DIFFICULTIES.items():
                        if event.key == d["key"]:
                            switch_difficulty(name)
                            break

            # swallow mouse clicks while entering initials (keyboard-driven)
            if entering_initials and event.type == pygame.MOUSEBUTTONDOWN:
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # any modal overlay: click closes it
                if show_scoreboard or show_about or show_shortcuts:
                    close_overlays()
                    continue

                # menu label toggle
                labels = menu_label_rects(font, menus)
                hit_label = None
                for label, items, rect in labels:
                    if rect.collidepoint(event.pos):
                        hit_label = label
                        break
                if hit_label is not None:
                    if open_menu == hit_label:
                        open_menu = None
                        open_submenu = None
                    else:
                        open_menu = hit_label
                        open_submenu = None
                    continue

                # a menu is open: resolve clicks inside its dropdown/submenu
                if open_menu is not None:
                    action = hovered_menu_action(font, menus, open_menu, open_submenu, event.pos)
                    if action is not None:
                        if isinstance(action, tuple) and action[0] == "submenu":
                            # toggle the submenu; find which item text owns it
                            for label, items, rect in labels:
                                if label == open_menu:
                                    _, item_rects = dropdown_rects(rect, items, font, below=True)
                                    for text, act, irect in item_rects:
                                        if isinstance(act, tuple) and act[0] == "submenu" and irect.collidepoint(event.pos):
                                            open_submenu = None if open_submenu == text else text
                                            break
                                    break
                        else:
                            do_action(action)
                            open_menu = None
                            open_submenu = None
                    else:
                        open_menu = None
                        open_submenu = None
                    continue

                # board interaction
                cell = cell_at(event.pos, board)
                if cell is None:
                    continue
                r, c = cell
                now = pygame.time.get_ticks()
                if last_click_cell == cell and now - last_click_time <= DOUBLE_CLICK_MS:
                    board.chord(r, c)
                    last_click_cell = None
                else:
                    board.reveal(r, c)
                    last_click_cell = cell
                    last_click_time = now

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if open_menu is None and not (show_scoreboard or show_about or show_shortcuts):
                    cell = cell_at(event.pos, board)
                    if cell is not None:
                        board.toggle_flag(*cell)

        # hover-open submenu when pointer sits over its parent row
        mouse_pos = pygame.mouse.get_pos()
        if open_menu is not None:
            for label, items, rect in menu_label_rects(font, menus):
                if label == open_menu:
                    _, item_rects = dropdown_rects(rect, items, font, below=True)
                    for text, act, irect in item_rects:
                        if isinstance(act, tuple) and act[0] == "submenu" and irect.collidepoint(mouse_pos):
                            open_submenu = text
                    break

        hover_item = hovered_menu_action(font, menus, open_menu, open_submenu, mouse_pos)

        draw(screen, board, font, big_font, mono, hover, W, H, difficulty, stats,
             current_elapsed())
        draw_menubar(screen, font, W, open_menu, open_submenu, hover_item, menus,
                     difficulty, settings["theme"])

        if entering_initials:
            draw_initials_overlay(screen, font, big_font, mono, W, H, difficulty,
                                  frozen_elapsed, initials, pending_rank)
        elif show_scoreboard:
            draw_scoreboard_overlay(screen, font, big_font, mono, W, H, stats)
        elif show_about:
            draw_about_overlay(screen, font, big_font, W, H)
        elif show_shortcuts:
            draw_shortcuts_overlay(screen, font, big_font, W, H)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
