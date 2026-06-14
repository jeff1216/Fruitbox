import sys
import os
import time
import threading
import argparse

import pygame
import pygame_gui
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from fruitbox_game import FruitBoxGame
from fruitbox_env import FruitBoxEnv
import fruitbox_stats
from fruitbox_pygame import (
    FPS, BG, CELL_BG, CELL_BORDER, CLEARED_BG,
    SEL_FILL, SEL_BORDER, VALID_FILL, VALID_BOR,
    TEXT_PRIMARY, TEXT_SECONDARY,
    TIMER_OK, TIMER_WARN, TIMER_DANGER,
    _THEME,
)
from solver import solve


def _resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


MODEL_PATH  = _resource("fruitbox_ppo_final")
AI_INTERVAL = 0.5

CELL    = 50
PADDING = 14
HUD_H   = 80
COLS    = 17
ROWS    = 10
GAP     = 24

BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
WIN_W   = BOARD_W * 2 + PADDING * 4 + GAP
WIN_H   = BOARD_H + PADDING * 2 + HUD_H

# HUD button layout — buttons are right-aligned from the AI board's right edge
_BTN_H = 26
_BTN_Y = (HUD_H - _BTN_H) // 2

# Pre-calculate right edge of AI board
_AI_BOARD_RIGHT = PADDING * 3 + BOARD_W + GAP + BOARD_W  # = WIN_W - PADDING


def mask_fn(env):
    return env.action_masks()


class FruitBoxVs:
    def __init__(self, opponent="solver", screen=None, grid_type="random"):
        self.opponent  = opponent
        self.grid_type = grid_type

        if screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        else:
            self.screen = screen
        pygame.display.set_caption(f"Fruit Box — vs {'Solver' if opponent == 'solver' else 'RL Model'}")
        self.clock = pygame.time.Clock()

        self.font_num   = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_score = pygame.font.SysFont("Arial", 23, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 15)
        self.font_over  = pygame.font.SysFont("Arial", 38, bold=True)
        self.font_sub   = pygame.font.SysFont("Arial", 20)
        self.font_btn   = pygame.font.SysFont("Arial", 13, bold=True)

        self.human_game = FruitBoxGame(grid_type=grid_type)
        self.ai_game    = FruitBoxGame(grid_type=grid_type)

        if opponent == "rl_model":
            self.ai_env  = ActionMasker(FruitBoxEnv(), mask_fn)
            self.ai_game = self.ai_env.env.game
            self.model   = MaskablePPO.load(MODEL_PATH)
        else:
            self.ai_env = None
            self.model  = None

        self.overlay          = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self.ai_board_visible = False
        self.close_over_rect  = pygame.Rect(0, 0, 0, 0)
        self.stats            = fruitbox_stats.get_vs_stats()

        # ── pygame_gui ────────────────────────────────────────────
        self.ui = pygame_gui.UIManager((WIN_W, WIN_H), _THEME)

        # Buttons placed right-to-left from AI board right edge
        rx = _AI_BOARD_RIGHT - PADDING

        # Show/Hide toggle (rightmost)
        self.toggle_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx - 60, _BTN_Y, 60, _BTN_H),
            text="Show",
            manager=self.ui,
        )
        rx -= 60 + 8

        # Pause
        self.pause_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx - 34, _BTN_Y, 34, _BTN_H),
            text="||",
            manager=self.ui,
        )
        rx -= 34 + 8

        # Menu
        self.menu_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx - 56, _BTN_Y, 56, _BTN_H),
            text="Menu",
            manager=self.ui,
        )
        rx -= 56 + 8

        # Restart
        self.restart_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx - 70, _BTN_Y, 70, _BTN_H),
            text="Restart",
            manager=self.ui,
        )

        self.reset()

    # ── board x offsets ───────────────────────────────────────────

    def _human_x(self):
        return PADDING

    def _ai_x(self):
        return PADDING * 3 + BOARD_W + GAP

    # ── geometry ──────────────────────────────────────────────────

    def _cell_rect(self, row, col, board_x):
        return pygame.Rect(
            board_x + col * CELL,
            HUD_H + PADDING + row * CELL,
            CELL - 1, CELL - 1,
        )

    def _pixel_to_cell(self, px, py):
        col = (px - self._human_x()) // CELL
        row = (py - HUD_H - PADDING) // CELL
        if 0 <= row < ROWS and 0 <= col < COLS:
            return row, col
        return None

    def _selection_bounds(self):
        if self.drag_start is None or self.drag_end is None:
            return None
        r1 = min(self.drag_start[0], self.drag_end[0])
        c1 = min(self.drag_start[1], self.drag_end[1])
        r2 = max(self.drag_start[0], self.drag_end[0])
        c2 = max(self.drag_start[1], self.drag_end[1])
        return r1, c1, r2, c2

    # ── drawing ───────────────────────────────────────────────────

    def _draw_board(self, game, board_x, drag_start=None, drag_end=None):
        for row in range(ROWS):
            for col in range(COLS):
                rect    = self._cell_rect(row, col, board_x)
                val     = game.grid[row][col]
                cleared = val == -1
                pygame.draw.rect(self.screen, CLEARED_BG if cleared else CELL_BG, rect, border_radius=5)
                pygame.draw.rect(self.screen, CELL_BORDER, rect, width=1, border_radius=5)
                if not cleared:
                    surf = self.font_num.render(str(val), True, TEXT_PRIMARY)
                    self.screen.blit(surf, (
                        rect.x + (CELL - 1 - surf.get_width())  // 2,
                        rect.y + (CELL - 1 - surf.get_height()) // 2,
                    ))

        if drag_start and drag_end:
            r1 = min(drag_start[0], drag_end[0])
            c1 = min(drag_start[1], drag_end[1])
            r2 = max(drag_start[0], drag_end[0])
            c2 = max(drag_start[1], drag_end[1])
            valid = game.validate_move(r1, c1, r2, c2)
            tl  = self._cell_rect(r1, c1, board_x)
            br  = self._cell_rect(r2, c2, board_x)
            sel = pygame.Rect(tl.x, tl.y, br.right - tl.x, br.bottom - tl.y)
            self.overlay.fill((0, 0, 0, 0))
            pygame.draw.rect(self.overlay, VALID_FILL if valid else SEL_FILL, sel, border_radius=8)
            self.screen.blit(self.overlay, (0, 0))
            pygame.draw.rect(self.screen, VALID_BOR if valid else SEL_BORDER, sel, width=2, border_radius=8)

    def _draw_hud(self):
        pygame.draw.rect(self.screen, (235, 233, 226), (0, 0, WIN_W, HUD_H))
        pygame.draw.line(self.screen, CELL_BORDER, (0, HUD_H), (WIN_W, HUD_H), 1)

        self.screen.blit(self.font_label.render("YOU", True, TEXT_SECONDARY), (self._human_x(), 12))
        self.screen.blit(self.font_score.render(str(self.human_game.score), True, TEXT_PRIMARY), (self._human_x(), 28))

        ai_label = "SOLVER" if self.opponent == "solver" else "RL MODEL"
        self.screen.blit(self.font_label.render(ai_label, True, TEXT_SECONDARY), (self._ai_x(), 12))
        self.screen.blit(self.font_score.render(str(self.ai_game.score), True, TEXT_PRIMARY), (self._ai_x(), 28))

        t    = self.human_game.time_remaining
        tcol = TIMER_OK if t > 30 else (TIMER_WARN if t > 10 else TIMER_DANGER)
        timer_surf = self.font_score.render(f"{int(t)}s", True, tcol)
        tx = (WIN_W - timer_surf.get_width()) // 2
        self.screen.blit(self.font_label.render("TIME", True, TEXT_SECONDARY), (tx, 12))
        self.screen.blit(timer_surf, (tx, 28))

        # Update dynamic button labels
        new_pause_text  = ">" if self.human_game.paused else "||"
        new_toggle_text = "Hide" if self.ai_board_visible else "Show"
        if self.pause_btn.text  != new_pause_text:
            self.pause_btn.set_text(new_pause_text)
        if self.toggle_btn.text != new_toggle_text:
            self.toggle_btn.set_text(new_toggle_text)

    def _draw_paused(self):
        grid_rect = pygame.Rect(self._human_x(), HUD_H + PADDING, BOARD_W, BOARD_H)
        pygame.draw.rect(self.screen, (180, 178, 170), grid_rect)
        surf = self.font_sub.render("Paused", True, TEXT_PRIMARY)
        self.screen.blit(surf, (
            grid_rect.x + (BOARD_W - surf.get_width())  // 2,
            grid_rect.y + (BOARD_H - surf.get_height()) // 2,
        ))

    def _draw_thinking(self):
        ax    = self._ai_x()
        cover = pygame.Rect(ax, HUD_H + PADDING, BOARD_W, BOARD_H)
        pygame.draw.rect(self.screen, (20, 20, 20), cover)
        dots = "." * (int(time.time() * 2) % 4)
        surf = self.font_sub.render(f"Solving{dots}", True, (200, 200, 200))
        self.screen.blit(surf, (
            ax + (BOARD_W - surf.get_width())  // 2,
            HUD_H + PADDING + (BOARD_H - surf.get_height()) // 2,
        ))

    def _draw_game_over(self):
        dim = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        dim.fill((44, 44, 42, 160))
        self.screen.blit(dim, (0, 0))

        card_w, card_h = 380, 185
        cx = (WIN_W - card_w) // 2
        cy = (WIN_H - card_h) // 2
        card = pygame.Rect(cx, cy, card_w, card_h)
        pygame.draw.rect(self.screen, (255, 255, 255), card, border_radius=14)
        pygame.draw.rect(self.screen, CELL_BORDER, card, width=1, border_radius=14)

        over  = self.font_over.render("Game Over", True, TEXT_PRIMARY)
        rsn   = self.font_sub.render(self.over_reason, True, TEXT_SECONDARY)
        again = self.font_sub.render("Press R to play again", True, TEXT_SECONDARY)
        w, l, t = self.stats["wins"], self.stats["losses"], self.stats["ties"]
        rec   = self.font_label.render(f"Record: {w}W  {l}L  {t}T", True, TEXT_SECONDARY)

        self.screen.blit(over,  (cx + (card_w - over.get_width())  // 2, cy + 22))
        self.screen.blit(rsn,   (cx + (card_w - rsn.get_width())   // 2, cy + 74))
        self.screen.blit(again, (cx + (card_w - again.get_width()) // 2, cy + 112))
        self.screen.blit(rec,   (cx + (card_w - rec.get_width())   // 2, cy + 154))

        x_surf = self.font_btn.render("X", True, TEXT_SECONDARY)
        x_pad  = 6
        x_w    = x_surf.get_width()  + x_pad * 2
        x_h    = x_surf.get_height() + x_pad * 2
        self.close_over_rect = pygame.Rect(cx + card_w - x_w - 8, cy + 8, x_w, x_h)
        if self.close_over_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (230, 228, 222), self.close_over_rect, border_radius=5)
        self.screen.blit(x_surf, (self.close_over_rect.x + x_pad, self.close_over_rect.y + x_pad))

    # ── AI logic ──────────────────────────────────────────────────

    def _run_solver(self, grid):
        solver_grid = [[0 if v == -1 else v for v in row] for row in grid]
        sol, _ = solve(solver_grid)
        self._solver_moves = sol['moves'][:]
        self._solver_ready = True

    def _step_ai(self):
        if self.opponent == "solver":
            if not self._solver_ready:
                return
            if not self._solver_moves:
                self.ai_over = True
                return
            _, r0, c0, r1, c1 = self._solver_moves.pop(0)
            self.ai_drag_start   = (r0, c0)
            self.ai_drag_end     = (r1, c1)
            self.ai_sel_clear_at = time.time() + 0.3
            _, no_moves = self.ai_game.apply_move(r0, c0, r1, c1)
            if no_moves:
                self.ai_over = True
        else:
            obs   = self.ai_env.env._obs()
            masks = self.ai_env.env.action_masks()
            action, _ = self.model.predict(obs, action_masks=masks, deterministic=True)
            r0, c0, r1, c1 = self.ai_env.env._decode(int(action))
            self.ai_drag_start   = (r0, c0)
            self.ai_drag_end     = (r1, c1)
            self.ai_sel_clear_at = time.time() + 0.2
            _, no_moves = self.ai_game.apply_move(r0, c0, r1, c1)
            if no_moves:
                self.ai_over = True

    # ── state ─────────────────────────────────────────────────────

    def reset(self):
        self.human_game.reset()

        if self.opponent == "rl_model":
            self.ai_env.reset()
            self.ai_game.grid = self.human_game.grid.copy()
        else:
            self.ai_game.reset()
            self.ai_game.grid = self.human_game.grid.copy()

        self.drag_start = None
        self.drag_end   = None

        self.ai_drag_start   = None
        self.ai_drag_end     = None
        self.ai_sel_clear_at = 0
        self.last_ai_move    = time.time() + AI_INTERVAL

        self.human_over       = False
        self.ai_over          = False
        self.game_over        = False
        self.over_reason      = ""
        self.show_game_over   = True
        self._result_recorded = False
        self._game_start      = time.time()

        self._solver_moves = []
        self._solver_ready = self.opponent != "solver"
        if self.opponent == "solver":
            threading.Thread(
                target=self._run_solver,
                args=(self.human_game.grid.tolist(),),
                daemon=True,
            ).start()

        self.pause_btn.enable()

    # ── main loop ─────────────────────────────────────────────────

    def run(self):
        self.clock.tick()
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.menu_btn:
                        return
                    if event.ui_element == self.restart_btn:
                        self.reset()
                    if event.ui_element == self.toggle_btn:
                        self.ai_board_visible = not self.ai_board_visible
                    if event.ui_element == self.pause_btn and not self.game_over:
                        self.human_game.toggle_pause()
                        self.drag_start = self.drag_end = None
                        if not self.human_game.paused:
                            self.last_ai_move = time.time() + AI_INTERVAL

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_r:
                        self.reset()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over and self.show_game_over and self.close_over_rect.collidepoint(event.pos):
                        self.show_game_over = False
                    else:
                        if self.game_over or (not self.human_over and not self.human_game.paused):
                            cell = self._pixel_to_cell(*event.pos)
                            if cell:
                                self.drag_start = self.drag_end = cell

                if event.type == pygame.MOUSEMOTION and self.drag_start:
                    if self.game_over or (not self.human_over and not self.human_game.paused):
                        cell = self._pixel_to_cell(*event.pos)
                        if cell:
                            self.drag_end = cell

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if not self.game_over and not self.human_over and not self.human_game.paused:
                        bounds = self._selection_bounds()
                        if bounds:
                            _, no_moves = self.human_game.apply_move(*bounds)
                            if no_moves:
                                self.human_over = True
                    self.drag_start = self.drag_end = None

                self.ui.process_events(event)

            if not self.game_over:
                timed_out = self.human_game.tick(dt)
                if not self.human_game.paused:
                    self.ai_game.elapsed = self.human_game.elapsed

                if timed_out:
                    self.human_over = self.ai_over = True

                now = time.time()

                if not self.ai_over and not self.human_game.paused and now >= self.last_ai_move:
                    self.last_ai_move = now + AI_INTERVAL
                    self._step_ai()

                if now >= self.ai_sel_clear_at:
                    self.ai_drag_start = self.ai_drag_end = None

                if self.human_over and self.ai_over:
                    self.game_over = True
                    h, a = self.human_game.score, self.ai_game.score
                    opp  = "Solver" if self.opponent == "solver" else "RL Model"
                    if   h > a: self.over_reason = f"You win!  {h} – {a}"
                    elif a > h: self.over_reason = f"{opp} wins!  {h} – {a}"
                    else:       self.over_reason = f"Tie!  {h} – {a}"
                    self.pause_btn.disable()
                    if not self._result_recorded:
                        fruitbox_stats.record(fruitbox_stats.GameInfo(
                            gamemode="vs_ai",
                            grid_type=self.grid_type,
                            self_score=h,
                            opp_score=a,
                            time_elapsed=time.time() - self._game_start,
                            seed=self.human_game.seed,
                        ))
                        self.stats = fruitbox_stats.get_vs_stats()
                        self._result_recorded = True

            self.screen.fill(BG)
            self._draw_hud()
            self._draw_board(self.human_game, self._human_x(), self.drag_start, self.drag_end)
            if self.human_game.paused:
                self._draw_paused()

            if self.opponent == "solver" and not self._solver_ready:
                self._draw_thinking()
            elif self.ai_board_visible:
                self._draw_board(self.ai_game, self._ai_x(), self.ai_drag_start, self.ai_drag_end)
            else:
                ai_cover = pygame.Rect(self._ai_x(), HUD_H + PADDING, BOARD_W, BOARD_H)
                pygame.draw.rect(self.screen, (0, 0, 0), ai_cover)

            self.ui.update(dt)
            self.ui.draw_ui(self.screen)

            if self.game_over and self.show_game_over:
                self._draw_game_over()

            pygame.display.flip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", choices=["solver", "rl_model"], default="solver")
    args = parser.parse_args()
    FruitBoxVs(opponent=args.opponent).run()
