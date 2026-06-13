import sys
import pygame

from fruitbox_game import FruitBoxGame
from fruitbox_pygame import (
    FruitBoxPygame,
    WIN_W as GAME_W, WIN_H as GAME_H,
    BG, TEXT_PRIMARY, TEXT_SECONDARY, CELL_BORDER,
)

MENU_W = GAME_W
MENU_H = GAME_H

BTN_W = 360
BTN_H = 80
BTN_GAP = 16
BTN_X = (MENU_W - BTN_W) // 2
BTN_Y_START = 190

ACCENT          = (24,  95, 165)
CARD_BG         = (255, 255, 255)
CARD_HOVER_BG   = (240, 246, 255)

TOGGLE_RANDOM   = (220, 235, 255)   # light blue pill
TOGGLE_SOLVABLE = (220, 245, 225)   # light green pill
TOGGLE_BORDER   = (24,  95, 165)
TOGGLE_TEXT     = (24,  95, 165)

MODES = [
    {
        "id":    "normal",
        "title": "Normal Mode",
        "desc":  "Random grid — classic gameplay",
    },
    {
        "id":    "solvable",
        "title": "Solvable Mode",
        "desc":  "Grid is guaranteed fully clearable",
    },
    {
        "id":    "vs_ai",
        "title": "VS AI",
        "desc":  "Race against the RL model side-by-side",
    },
    {
        "id":    "watch_ai",
        "title": "Watch AI",
        "desc":  "Sit back and watch the RL model play",
    },
]

VS_AI_IDX    = 2   # index of the vs_ai entry in MODES
WATCH_AI_IDX = 3   # index of the watch_ai entry in MODES


class FruitBoxMenu:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((MENU_W, MENU_H))
        pygame.display.set_caption("Fruit Box")
        self.clock        = pygame.time.Clock()
        self.font_title   = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_sub     = pygame.font.SysFont("Arial", 15)
        self.font_btn     = pygame.font.SysFont("Arial", 21, bold=True)
        self.font_desc    = pygame.font.SysFont("Arial", 14)
        self.font_hint    = pygame.font.SysFont("Arial", 12)
        self.font_toggle  = pygame.font.SysFont("Arial", 12, bold=True)

        self.vs_grid_type      = "random"
        self.vs_toggle_rect    = pygame.Rect(0, 0, 0, 0)
        self.watch_grid_type   = "solvable"
        self.watch_toggle_rect = pygame.Rect(0, 0, 0, 0)

    # ── geometry ──────────────────────────────────────────────────────

    def _btn_rect(self, idx):
        y = BTN_Y_START + idx * (BTN_H + BTN_GAP)
        return pygame.Rect(BTN_X, y, BTN_W, BTN_H)

    # ── drawing ───────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(BG)

        title = self.font_title.render("Fruit Box", True, TEXT_PRIMARY)
        self.screen.blit(title, ((MENU_W - title.get_width()) // 2, 100))

        sub = self.font_sub.render("Choose a game mode to start", True, TEXT_SECONDARY)
        self.screen.blit(sub, ((MENU_W - sub.get_width()) // 2, 100 + title.get_height() + 10))

        mouse = pygame.mouse.get_pos()
        for i, mode in enumerate(MODES):
            rect    = self._btn_rect(i)
            hovered = rect.collidepoint(mouse) and not (
                (i == VS_AI_IDX    and self.vs_toggle_rect.collidepoint(mouse)) or
                (i == WATCH_AI_IDX and self.watch_toggle_rect.collidepoint(mouse))
            )

            pygame.draw.rect(self.screen, CARD_HOVER_BG if hovered else CARD_BG, rect, border_radius=12)
            pygame.draw.rect(
                self.screen,
                ACCENT if hovered else CELL_BORDER,
                rect, width=2 if hovered else 1, border_radius=12,
            )

            t_surf = self.font_btn.render(mode["title"], True, TEXT_PRIMARY)
            d_surf = self.font_desc.render(mode["desc"],  True, TEXT_SECONDARY)
            content_h = t_surf.get_height() + 5 + d_surf.get_height()
            ty = rect.y + (BTN_H - content_h) // 2
            tx = rect.x + 22
            self.screen.blit(t_surf, (tx, ty))
            self.screen.blit(d_surf, (tx, ty + t_surf.get_height() + 5))

            # grid-type toggle pill on VS AI and Watch AI cards
            if i == VS_AI_IDX:
                label    = self.vs_grid_type.capitalize()
                tgl_surf = self.font_toggle.render(label, True, TOGGLE_TEXT)
                pad_x, pad_y = 10, 5
                tgl_w = tgl_surf.get_width()  + pad_x * 2
                tgl_h = tgl_surf.get_height() + pad_y * 2
                tgl_x = rect.right - tgl_w - 14
                tgl_y = rect.y + (BTN_H - tgl_h) // 2
                self.vs_toggle_rect = pygame.Rect(tgl_x, tgl_y, tgl_w, tgl_h)

                pill_bg = TOGGLE_RANDOM if self.vs_grid_type == "random" else TOGGLE_SOLVABLE
                tgl_hov = self.vs_toggle_rect.collidepoint(mouse)
                if tgl_hov:
                    r, g, b = pill_bg
                    pill_bg = (max(r - 15, 0), max(g - 15, 0), max(b - 15, 0))

                pygame.draw.rect(self.screen, pill_bg, self.vs_toggle_rect, border_radius=20)
                pygame.draw.rect(self.screen, TOGGLE_BORDER, self.vs_toggle_rect, width=1, border_radius=20)
                self.screen.blit(tgl_surf, (tgl_x + pad_x, tgl_y + pad_y))

            if i == WATCH_AI_IDX:
                label    = self.watch_grid_type.capitalize()
                tgl_surf = self.font_toggle.render(label, True, TOGGLE_TEXT)
                pad_x, pad_y = 10, 5
                tgl_w = tgl_surf.get_width()  + pad_x * 2
                tgl_h = tgl_surf.get_height() + pad_y * 2
                tgl_x = rect.right - tgl_w - 14
                tgl_y = rect.y + (BTN_H - tgl_h) // 2
                self.watch_toggle_rect = pygame.Rect(tgl_x, tgl_y, tgl_w, tgl_h)

                pill_bg = TOGGLE_RANDOM if self.watch_grid_type == "random" else TOGGLE_SOLVABLE
                tgl_hov = self.watch_toggle_rect.collidepoint(mouse)
                if tgl_hov:
                    r, g, b = pill_bg
                    pill_bg = (max(r - 15, 0), max(g - 15, 0), max(b - 15, 0))

                pygame.draw.rect(self.screen, pill_bg, self.watch_toggle_rect, border_radius=20)
                pygame.draw.rect(self.screen, TOGGLE_BORDER, self.watch_toggle_rect, width=1, border_radius=20)
                self.screen.blit(tgl_surf, (tgl_x + pad_x, tgl_y + pad_y))

        hint = self.font_hint.render("Press ESC during a game to return here", True, TEXT_SECONDARY)
        self.screen.blit(hint, ((MENU_W - hint.get_width()) // 2, MENU_H - 26))

        pygame.display.flip()

    # ── menu loop ─────────────────────────────────────────────────────

    def _menu_loop(self):
        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # toggle pills take priority over card click
                    if self.vs_toggle_rect.collidepoint(event.pos):
                        self.vs_grid_type = "solvable" if self.vs_grid_type == "random" else "random"
                        continue
                    if self.watch_toggle_rect.collidepoint(event.pos):
                        self.watch_grid_type = "solvable" if self.watch_grid_type == "random" else "random"
                        continue
                    for i, mode in enumerate(MODES):
                        if self._btn_rect(i).collidepoint(event.pos):
                            return mode["id"]
            self._draw()

    # ── launchers ─────────────────────────────────────────────────────

    def _launch(self, mode):
        if mode in ("normal", "solvable"):
            grid_type = "random" if mode == "normal" else "solvable"
            game   = FruitBoxGame(grid_type=grid_type)
            game.reset()
            screen = pygame.display.set_mode((GAME_W, GAME_H))
            FruitBoxPygame(game=game, screen=screen).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

        elif mode == "vs_ai":
            from fruitbox_vs import FruitBoxVs, WIN_W as VS_W, WIN_H as VS_H
            screen = pygame.display.set_mode((VS_W, VS_H))
            screen.fill(BG)
            loading_surf = self.font_btn.render("Loading model…", True, TEXT_SECONDARY)
            screen.blit(loading_surf, (
                (VS_W - loading_surf.get_width())  // 2,
                (VS_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()
            FruitBoxVs(opponent="rl_model", screen=screen, grid_type=self.vs_grid_type).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

        elif mode == "watch_ai":
            from fruitbox_ai_watch import FruitBoxAiWatch
            screen = pygame.display.set_mode((GAME_W, GAME_H))
            screen.fill(BG)
            loading_surf = self.font_btn.render("Loading model…", True, TEXT_SECONDARY)
            screen.blit(loading_surf, (
                (GAME_W - loading_surf.get_width())  // 2,
                (GAME_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()
            FruitBoxAiWatch(screen=screen, grid_type=self.watch_grid_type).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

    # ── main ──────────────────────────────────────────────────────────

    def run(self):
        while True:
            mode = self._menu_loop()
            self._launch(mode)


if __name__ == "__main__":
    FruitBoxMenu().run()
