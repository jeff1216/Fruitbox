import asyncio
import math
import time
import pygame
import pygame_gui

from fruitbox.ai_watch import FruitBoxAiWatch, AI_INTERVAL
from fruitbox import colors as fruitbox_colors
from fruitbox import config as fruitbox_config
from ._common import ONNX_PATH


class WebAiWatch(FruitBoxAiWatch):
    """FruitBoxAiWatch using OnnxAgent with an async run() for pygbag."""

    def _create_model(self):
        from fruitbox.onnx_agent import OnnxAgent
        return OnnxAgent(ONNX_PATH)

    async def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.menu_btn:
                        return
                    if event.ui_element == self.restart_btn:
                        self.reset()

                if event.type == pygame.KEYDOWN:
                    if event.key == fruitbox_config.get("key_menu"):
                        return
                    if event.key == pygame.K_r:
                        self.reset()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over and self.show_game_over and self.close_over_rect.collidepoint(event.pos):
                        self.show_game_over = False

                self.ui.process_events(event)

            if not self.game_over:
                timed_out = self.game.tick(dt)
                if timed_out:
                    self.game_over    = True
                    self.game_over_at = time.time()

                now = time.time()
                if now >= self.last_ai_move:
                    self.last_ai_move = now + AI_INTERVAL
                    self._step_ai()
                if now >= self.sel_clear_at:
                    self.sel_start = self.sel_end = None

            if self.game_over and self.show_game_over and self.game_over_at is not None:
                if time.time() - self.game_over_at >= 5.0:
                    self.reset()
                    continue

            self.screen.fill(fruitbox_colors.C["BG"])
            self._draw_hud()
            self._draw_board()

            self.ui.update(dt)
            self.ui.draw_ui(self.screen)

            btn_r = self.restart_btn.get_abs_rect()
            self.screen.blit(self._icon_restart, self._icon_restart.get_rect(center=btn_r.center))

            if self.game_over and self.show_game_over:
                self._draw_game_over()

            pygame.display.flip()
            await asyncio.sleep(0)
