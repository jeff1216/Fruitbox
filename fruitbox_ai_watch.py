import sys
import os
import time

import pygame
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from fruitbox_env import FruitBoxEnv
from fruitbox_pygame import (
    FPS, CELL, PADDING, HUD_H, COLS, ROWS, WIN_W, WIN_H,
    BG, CELL_BG, CELL_BORDER, CLEARED_BG,
    TEXT_PRIMARY, TEXT_SECONDARY,
    TIMER_OK, TIMER_WARN, TIMER_DANGER,
    BTN_COLOR, BTN_HOVER_COLOR, BTN_BORDER_COLOR,
    VALID_FILL, VALID_BOR,
)


def _resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


MODEL_PATH  = _resource("fruitbox_ppo_final")
AI_INTERVAL = 0.5


def mask_fn(env):
    return env.action_masks()


class FruitBoxAiWatch:
    def __init__(self, screen=None, grid_type="solvable"):
        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        else:
            self.screen = screen
        pygame.display.set_caption("Fruit Box — Watch AI")
        self.clock = pygame.time.Clock()

        self.font_num   = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_score = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 13)
        self.font_over  = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_sub   = pygame.font.SysFont("Arial", 18)
        self.font_btn   = pygame.font.SysFont("Arial", 13, bold=True)

        self.ai_env = ActionMasker(FruitBoxEnv(grid_type=grid_type), mask_fn)
        self.game   = self.ai_env.env.game
        self.model  = MaskablePPO.load(MODEL_PATH)

        self.overlay          = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self.menu_btn_rect    = pygame.Rect(0, 0, 0, 0)
        self.restart_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.close_over_rect  = pygame.Rect(0, 0, 0, 0)
        self.reset()

    def reset(self):
        self.ai_env.reset()
        self.game_over       = False
        self.show_game_over  = True
        self.last_ai_move    = time.time() + AI_INTERVAL
        self.sel_start       = None
        self.sel_end         = None
        self.sel_clear_at    = 0

    # ── drawing ───────────────────────────────────────────────────────

    def _cell_rect(self, row, col):
        return pygame.Rect(
            PADDING + col * CELL,
            HUD_H + PADDING + row * CELL,
            CELL - 1, CELL - 1,
        )

    def _draw_hud(self):
        pygame.draw.rect(self.screen, (235, 233, 226), (0, 0, WIN_W, HUD_H))
        pygame.draw.line(self.screen, CELL_BORDER, (0, HUD_H), (WIN_W, HUD_H), 1)

        self.screen.blit(self.font_label.render("SCORE", True, TEXT_SECONDARY), (PADDING, 12))
        self.screen.blit(self.font_score.render(str(self.game.score), True, TEXT_PRIMARY), (PADDING, 28))

        t    = self.game.time_remaining
        tcol = TIMER_OK if t > 30 else (TIMER_WARN if t > 10 else TIMER_DANGER)
        bar_w  = 180
        bar_x  = WIN_W - PADDING - bar_w
        self.screen.blit(self.font_label.render("TIME", True, TEXT_SECONDARY), (bar_x, 12))
        self.screen.blit(self.font_score.render(f"{int(t)}s", True, tcol), (bar_x, 28))
        bar_y, bar_h = 48, 6
        fill_w = int(bar_w * (t / self.game.time_limit))
        pygame.draw.rect(self.screen, CELL_BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        pygame.draw.rect(self.screen, tcol, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        mouse = pygame.mouse.get_pos()
        btn_pad_x, btn_pad_y = 10, 5
        m_surf = self.font_btn.render("Menu", True, TEXT_PRIMARY)
        m_w    = m_surf.get_width()  + btn_pad_x * 2
        m_h    = m_surf.get_height() + btn_pad_y * 2
        m_x    = PADDING + 90
        m_y    = (HUD_H - m_h) // 2
        self.menu_btn_rect = pygame.Rect(m_x, m_y, m_w, m_h)
        m_hov  = self.menu_btn_rect.collidepoint(mouse)
        pygame.draw.rect(self.screen, BTN_HOVER_COLOR if m_hov else BTN_COLOR, self.menu_btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, BTN_BORDER_COLOR, self.menu_btn_rect, width=1, border_radius=5)
        self.screen.blit(m_surf, (m_x + btn_pad_x, m_y + btn_pad_y))

        r_surf = self.font_btn.render("Restart", True, TEXT_PRIMARY)
        r_w    = r_surf.get_width()  + btn_pad_x * 2
        r_h    = r_surf.get_height() + btn_pad_y * 2
        r_x    = m_x + m_w + 8
        r_y    = (HUD_H - r_h) // 2
        self.restart_btn_rect = pygame.Rect(r_x, r_y, r_w, r_h)
        r_hov  = self.restart_btn_rect.collidepoint(mouse)
        pygame.draw.rect(self.screen, BTN_HOVER_COLOR if r_hov else BTN_COLOR, self.restart_btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, BTN_BORDER_COLOR, self.restart_btn_rect, width=1, border_radius=5)
        self.screen.blit(r_surf, (r_x + btn_pad_x, r_y + btn_pad_y))

    def _draw_board(self):
        for row in range(ROWS):
            for col in range(COLS):
                rect    = self._cell_rect(row, col)
                val     = self.game.grid[row][col]
                cleared = val == -1
                pygame.draw.rect(self.screen, CLEARED_BG if cleared else CELL_BG, rect, border_radius=6)
                pygame.draw.rect(self.screen, CELL_BORDER, rect, width=1, border_radius=6)
                if not cleared:
                    surf = self.font_num.render(str(val), True, TEXT_PRIMARY)
                    self.screen.blit(surf, (
                        rect.x + (CELL - 1 - surf.get_width())  // 2,
                        rect.y + (CELL - 1 - surf.get_height()) // 2,
                    ))

        if self.sel_start and self.sel_end:
            r1 = min(self.sel_start[0], self.sel_end[0])
            c1 = min(self.sel_start[1], self.sel_end[1])
            r2 = max(self.sel_start[0], self.sel_end[0])
            c2 = max(self.sel_start[1], self.sel_end[1])
            tl  = self._cell_rect(r1, c1)
            br  = self._cell_rect(r2, c2)
            sel = pygame.Rect(tl.x, tl.y, br.right - tl.x, br.bottom - tl.y)
            self.overlay.fill((0, 0, 0, 0))
            pygame.draw.rect(self.overlay, VALID_FILL, sel, border_radius=8)
            self.screen.blit(self.overlay, (0, 0))
            pygame.draw.rect(self.screen, VALID_BOR, sel, width=2, border_radius=8)

    def _draw_game_over(self):
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((44, 44, 42, 160))
        self.screen.blit(dim, (0, 0))

        card_w, card_h = 340, 160
        cx = (WIN_W - card_w) // 2
        cy = (WIN_H - card_h) // 2
        card = pygame.Rect(cx, cy, card_w, card_h)
        pygame.draw.rect(self.screen, (255, 255, 255), card, border_radius=14)
        pygame.draw.rect(self.screen, CELL_BORDER, card, width=1, border_radius=14)

        over  = self.font_over.render("Done", True, TEXT_PRIMARY)
        score = self.font_sub.render(f"Final score: {self.game.score}", True, TEXT_SECONDARY)
        again = self.font_sub.render("Press R to watch again", True, TEXT_SECONDARY)
        self.screen.blit(over,  (cx + (card_w - over.get_width())  // 2, cy + 20))
        self.screen.blit(score, (cx + (card_w - score.get_width()) // 2, cy + 72))
        self.screen.blit(again, (cx + (card_w - again.get_width()) // 2, cy + 112))

        x_surf = self.font_btn.render("X", True, TEXT_SECONDARY)
        x_pad  = 6
        x_w    = x_surf.get_width()  + x_pad * 2
        x_h    = x_surf.get_height() + x_pad * 2
        self.close_over_rect = pygame.Rect(cx + card_w - x_w - 8, cy + 8, x_w, x_h)
        if self.close_over_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (230, 228, 222), self.close_over_rect, border_radius=5)
        self.screen.blit(x_surf, (self.close_over_rect.x + x_pad, self.close_over_rect.y + x_pad))

    # ── AI ────────────────────────────────────────────────────────────

    def _step_ai(self):
        obs    = self.ai_env.env._obs()
        masks  = self.ai_env.env.action_masks()
        action, _ = self.model.predict(obs, action_masks=masks, deterministic=True)
        r0, c0, r1, c1 = self.ai_env.env._decode(int(action))
        self.sel_start    = (r0, c0)
        self.sel_end      = (r1, c1)
        self.sel_clear_at = time.time() + 0.3
        _, no_moves = self.game.apply_move(r0, c0, r1, c1)
        if no_moves:
            self.game_over = True

    # ── main loop ─────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_r:
                        self.reset()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over and self.show_game_over and self.close_over_rect.collidepoint(event.pos):
                        self.show_game_over = False
                        continue
                    if self.menu_btn_rect.collidepoint(event.pos):
                        return
                    if self.restart_btn_rect.collidepoint(event.pos):
                        self.reset()
                        continue

            if not self.game_over:
                timed_out = self.game.tick(dt)
                if timed_out:
                    self.game_over = True

                now = time.time()
                if now >= self.last_ai_move:
                    self.last_ai_move = now + AI_INTERVAL
                    self._step_ai()
                if now >= self.sel_clear_at:
                    self.sel_start = self.sel_end = None

            self.screen.fill(BG)
            self._draw_hud()
            self._draw_board()
            if self.game_over and self.show_game_over:
                self._draw_game_over()
            pygame.display.flip()
