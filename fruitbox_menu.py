import sys
import pygame

from fruitbox_game import FruitBoxGame
from fruitbox_settings import SettingsOverlay
from fruitbox_pygame import (
    FruitBoxPygame,
    WIN_W as GAME_W, WIN_H as GAME_H,
    BG, TEXT_PRIMARY, TEXT_SECONDARY, CELL_BORDER,
)

MENU_W = GAME_W
MENU_H = GAME_H

ACCENT        = (24,  95, 165)
CARD_BG       = (255, 255, 255)
CARD_HOVER_BG = (240, 246, 255)
ARROW_COLOR   = (220, 130, 50)
ARROW_HOVER   = (180,  90, 20)

GRID_TYPES = ["random", "solvable"]


class FruitBoxMenu:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((MENU_W, MENU_H))
        pygame.display.set_caption("Fruit Box")
        self.clock        = pygame.time.Clock()
        self.font_title   = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_btn     = pygame.font.SysFont("Arial", 21, bold=True)
        self.font_hint    = pygame.font.SysFont("Arial", 12)
        self.font_toggle  = pygame.font.SysFont("Arial", 15, bold=True)
        self.font_arrow   = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_label   = pygame.font.SysFont("Arial", 15)

        self.grid_type_idx    = 0
        self.sp_btn_rect      = pygame.Rect(0, 0, 0, 0)
        self.vs_btn_rect      = pygame.Rect(0, 0, 0, 0)
        self.left_arrow_rect  = pygame.Rect(0, 0, 0, 0)
        self.right_arrow_rect = pygame.Rect(0, 0, 0, 0)
        self.settings          = SettingsOverlay()
        self.settings_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.watch_btn_rect    = pygame.Rect(MENU_W - 60, MENU_H - 30, 60, 30)

    @property
    def grid_type(self):
        return GRID_TYPES[self.grid_type_idx]

    # ── drawing ───────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(BG)
        mouse = pygame.mouse.get_pos()

        # title
        title = self.font_title.render("Fruit Box", True, TEXT_PRIMARY)
        self.screen.blit(title, ((MENU_W - title.get_width()) // 2, 100))

        # mode cards (side by side)
        card_w = 280
        card_h = 80
        card_gap = 24
        card_y = 240
        cards_x = (MENU_W - card_w * 2 - card_gap) // 2

        self.sp_btn_rect = pygame.Rect(cards_x,                   card_y, card_w, card_h)
        self.vs_btn_rect = pygame.Rect(cards_x + card_w + card_gap, card_y, card_w, card_h)

        for rect, label in [(self.sp_btn_rect, "Single Player"), (self.vs_btn_rect, "vs AI")]:
            hovered = rect.collidepoint(mouse)
            pygame.draw.rect(self.screen, CARD_HOVER_BG if hovered else CARD_BG, rect, border_radius=12)
            pygame.draw.rect(self.screen, ACCENT if hovered else CELL_BORDER, rect,
                             width=2 if hovered else 1, border_radius=12)
            surf = self.font_btn.render(label, True, TEXT_PRIMARY)
            self.screen.blit(surf, (
                rect.x + (card_w - surf.get_width())  // 2,
                rect.y + (card_h - surf.get_height()) // 2,
            ))

        # grid type selector
        gt_cy = card_y + card_h + 60

        label_surf = self.font_btn.render("Grid Type", True, TEXT_SECONDARY)
        pill_surf  = self.font_btn.render(self.grid_type.capitalize(), True, ACCENT)
        pill_pad_x, pill_pad_y = 20, 8
        pill_w = max(pill_surf.get_width() + pill_pad_x * 2, 140)
        pill_h = pill_surf.get_height() + pill_pad_y * 2

        arr_l      = self.font_arrow.render("<", True, ARROW_COLOR)
        arr_r      = self.font_arrow.render(">", True, ARROW_COLOR)
        arr_click_w = arr_l.get_width() + 24
        spacing    = 18

        total_w = (label_surf.get_width() + spacing +
                   arr_click_w + spacing +
                   pill_w + spacing +
                   arr_click_w)
        row_x = (MENU_W - total_w) // 2

        # "Grid Type" label
        self.screen.blit(label_surf, (row_x, gt_cy - label_surf.get_height() // 2))
        x = row_x + label_surf.get_width() + spacing

        # left arrow
        self.left_arrow_rect = pygame.Rect(x, gt_cy - pill_h // 2, arr_click_w, pill_h)
        l_hov = self.left_arrow_rect.collidepoint(mouse)
        self.screen.blit(
            self.font_arrow.render("<", True, ARROW_HOVER if l_hov else ARROW_COLOR),
            (x + 12, gt_cy - arr_l.get_height() // 2),
        )
        x += arr_click_w + spacing

        # pill
        pill_rect = pygame.Rect(x, gt_cy - pill_h // 2, pill_w, pill_h)
        pygame.draw.rect(self.screen, (220, 235, 255), pill_rect, border_radius=20)
        pygame.draw.rect(self.screen, ACCENT, pill_rect, width=2, border_radius=20)
        self.screen.blit(pill_surf, (
            x + (pill_w - pill_surf.get_width())  // 2,
            gt_cy - pill_surf.get_height() // 2,
        ))
        x += pill_w + spacing

        # right arrow
        self.right_arrow_rect = pygame.Rect(x, gt_cy - pill_h // 2, arr_click_w, pill_h)
        r_hov = self.right_arrow_rect.collidepoint(mouse)
        self.screen.blit(
            self.font_arrow.render(">", True, ARROW_HOVER if r_hov else ARROW_COLOR),
            (x + 12, gt_cy - arr_r.get_height() // 2),
        )

        # hint
        hint = self.font_hint.render("Press ESC during a game to return here", True, TEXT_SECONDARY)
        self.screen.blit(hint, ((MENU_W - hint.get_width()) // 2, MENU_H - 26))

        # settings button (top-right corner)
        s_surf = self.font_hint.render("Settings", True, TEXT_SECONDARY)
        s_pad_x, s_pad_y = 10, 5
        s_w = s_surf.get_width()  + s_pad_x * 2
        s_h = s_surf.get_height() + s_pad_y * 2
        s_x = MENU_W - s_w - 14
        s_y = 14
        self.settings_btn_rect = pygame.Rect(s_x, s_y, s_w, s_h)
        s_hov = self.settings_btn_rect.collidepoint(mouse)
        pygame.draw.rect(self.screen, (190, 188, 180) if s_hov else (210, 208, 200), self.settings_btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, (160, 158, 150), self.settings_btn_rect, width=1, border_radius=5)
        self.screen.blit(s_surf, (s_x + s_pad_x, s_y + s_pad_y))

        self.settings.draw(self.screen)
        pygame.display.flip()

    # ── menu loop ─────────────────────────────────────────────────────

    def _menu_loop(self):
        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.settings.handle_event(event):
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.settings_btn_rect.collidepoint(event.pos):
                        self.settings.toggle()
                        continue
                    if self.left_arrow_rect.collidepoint(event.pos):
                        self.grid_type_idx = (self.grid_type_idx - 1) % len(GRID_TYPES)
                        continue
                    if self.right_arrow_rect.collidepoint(event.pos):
                        self.grid_type_idx = (self.grid_type_idx + 1) % len(GRID_TYPES)
                        continue
                    if self.sp_btn_rect.collidepoint(event.pos):
                        return "single_player"
                    if self.vs_btn_rect.collidepoint(event.pos):
                        return "vs_ai"
                    if self.watch_btn_rect.collidepoint(event.pos):
                        return "watch_ai"
            self._draw()

    # ── launchers ─────────────────────────────────────────────────────

    def _launch(self, mode):
        if mode == "single_player":
            game = FruitBoxGame(grid_type=self.grid_type)
            game.reset()
            screen = pygame.display.set_mode((GAME_W, GAME_H))
            FruitBoxPygame(game=game, screen=screen).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

        elif mode == "vs_ai":
            # Show loading on the current menu screen immediately (before any heavy imports)
            loading_surf = self.font_btn.render("Loading model…", True, TEXT_SECONDARY)
            self.screen.fill(BG)
            self.screen.blit(loading_surf, (
                (MENU_W - loading_surf.get_width())  // 2,
                (MENU_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()

            from fruitbox_vs import FruitBoxVs, WIN_W as VS_W, WIN_H as VS_H
            screen = pygame.display.set_mode((VS_W, VS_H))
            screen.fill(BG)
            screen.blit(loading_surf, (
                (VS_W - loading_surf.get_width())  // 2,
                (VS_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()
            FruitBoxVs(opponent="rl_model", screen=screen, grid_type=self.grid_type).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

        elif mode == "watch_ai":
            loading_surf = self.font_btn.render("Loading model…", True, TEXT_SECONDARY)
            self.screen.fill(BG)
            self.screen.blit(loading_surf, (
                (MENU_W - loading_surf.get_width())  // 2,
                (MENU_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()

            from fruitbox_ai_watch import FruitBoxAiWatch
            screen = pygame.display.set_mode((GAME_W, GAME_H))
            screen.fill(BG)
            screen.blit(loading_surf, (
                (GAME_W - loading_surf.get_width())  // 2,
                (GAME_H - loading_surf.get_height()) // 2,
            ))
            pygame.display.flip()
            FruitBoxAiWatch(screen=screen, grid_type=self.grid_type).run()
            self.screen = pygame.display.set_mode((MENU_W, MENU_H))

    # ── main ──────────────────────────────────────────────────────────

    def run(self):
        while True:
            mode = self._menu_loop()
            self._launch(mode)


if __name__ == "__main__":
    FruitBoxMenu().run()
