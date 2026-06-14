import pygame
import time
import subprocess
import fruitbox_stats

_TEXT_PRIMARY   = (44,  44,  42)
_TEXT_SECONDARY = (95,  94,  90)
_CELL_BORDER    = (210, 208, 200)
_DIVIDER        = (220, 218, 210)
_ROW_ALT        = (248, 247, 244)
_ROW_SEL        = (220, 235, 255)
_ROW_HOV        = (235, 233, 226)

_MODE_LABEL = {
    "single_player": "Single",
    "vs_ai":         "VS AI",
    "watch_ai":      "Watch AI",
}


def _fmt_time(seconds):
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s}s"
    else:
        h, rem = divmod(seconds, 3600)
        return f"{h}h {rem // 60}m"


def _to_clipboard(text):
    try:
        subprocess.run("clip", input=text.encode("utf-16-le"), check=True, shell=True)
    except Exception:
        pass


class StatsOverlay:
    def __init__(self):
        self.visible          = False
        self._view            = "stats"
        self._card_rect       = pygame.Rect(0, 0, 0, 0)
        self.close_rect       = pygame.Rect(0, 0, 0, 0)
        self.history_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.back_btn_rect    = pygame.Rect(0, 0, 0, 0)
        self._font_title      = None
        self._font_label      = None
        self._font_value      = None
        self._font_btn        = None
        self._font_col        = None
        self._summary         = None
        self._history         = []
        self._scroll          = 0
        self._row_h           = 24
        self._visible_rows    = 0
        self._row_area_rect   = pygame.Rect(0, 0, 0, 0)
        self._selected_row    = None
        self._copied_at       = 0.0
        self._random_seed_rect   = pygame.Rect(0, 0, 0, 0)
        self._solvable_seed_rect = pygame.Rect(0, 0, 0, 0)

    def _ensure_fonts(self):
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("Arial", 26, bold=True)
            self._font_label = pygame.font.SysFont("Arial", 12)
            self._font_value = pygame.font.SysFont("Arial", 18, bold=True)
            self._font_btn   = pygame.font.SysFont("Arial", 13, bold=True)
            self._font_col   = pygame.font.SysFont("Arial", 13)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self._view         = "stats"
            self._scroll       = 0
            self._selected_row = None
            self._summary      = fruitbox_stats.get_summary()

    def _open_history(self):
        self._view         = "history"
        self._scroll       = 0
        self._selected_row = None
        self._history      = fruitbox_stats.get_history()

    def handle_event(self, event):
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._view == "history":
                    self._view = "stats"
                else:
                    self.visible = False
            return True
        if event.type == pygame.MOUSEWHEEL and self._view == "history":
            max_scroll = max(0, len(self._history) - self._visible_rows)
            self._scroll = max(0, min(self._scroll - event.y, max_scroll))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                self.visible = False
                return True
            if self._view == "stats":
                if self.history_btn_rect.collidepoint(event.pos):
                    self._open_history()
                    return True
                s = self._summary
                if s and self._random_seed_rect.collidepoint(event.pos) and s["random_best_seed"] is not None:
                    _to_clipboard(str(s["random_best_seed"]))
                    self._copied_at = time.time()
                if s and self._solvable_seed_rect.collidepoint(event.pos) and s["solvable_best_seed"] is not None:
                    _to_clipboard(str(s["solvable_best_seed"]))
                    self._copied_at = time.time()
            elif self._view == "history":
                if self.back_btn_rect.collidepoint(event.pos):
                    self._view = "stats"
                    return True
                if self._row_area_rect.collidepoint(event.pos):
                    idx = (event.pos[1] - self._row_area_rect.y) // self._row_h + self._scroll
                    if 0 <= idx < len(self._history):
                        self._selected_row = idx
                        _to_clipboard(str(self._history[idx]["seed"]))
                        self._copied_at = time.time()
            if not self._card_rect.collidepoint(event.pos):
                self.visible = False
            return True
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            return True
        return False

    # ── shared helpers ────────────────────────────────────────────────

    def _draw_card(self, screen, card_w, card_h):
        w, h = screen.get_size()
        cx = (w - card_w) // 2
        cy = (h - card_h) // 2
        self._card_rect = pygame.Rect(cx, cy, card_w, card_h)

        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((44, 44, 42, 160))
        screen.blit(dim, (0, 0))

        pygame.draw.rect(screen, (255, 255, 255), self._card_rect, border_radius=14)
        pygame.draw.rect(screen, _CELL_BORDER, self._card_rect, width=1, border_radius=14)

        x_surf = self._font_btn.render("X", True, _TEXT_SECONDARY)
        x_pad  = 6
        x_w    = x_surf.get_width()  + x_pad * 2
        x_h    = x_surf.get_height() + x_pad * 2
        self.close_rect = pygame.Rect(cx + card_w - x_w - 8, cy + 8, x_w, x_h)
        if self.close_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, (230, 228, 222), self.close_rect, border_radius=5)
        screen.blit(x_surf, (self.close_rect.x + x_pad, self.close_rect.y + x_pad))

        return cx, cy

    def _draw_copied_toast(self, screen, cx, cy, card_w, card_h):
        if time.time() - self._copied_at < 1.2:
            toast = self._font_label.render("Copied!", True, (15, 110, 86))
            screen.blit(toast, (cx + card_w - toast.get_width() - 12,
                                cy + card_h - toast.get_height() - 10))

    # ── stats view ────────────────────────────────────────────────────

    def _draw_stats(self, screen):
        s      = self._summary
        card_w = 440
        card_h = 360
        cx, cy = self._draw_card(screen, card_w, card_h)
        pad    = 32
        mouse  = pygame.mouse.get_pos()

        title = self._font_title.render("Stats", True, _TEXT_PRIMARY)
        screen.blit(title, (cx + (card_w - title.get_width()) // 2, cy + 20))

        y = cy + 66

        def row(label, value):
            nonlocal y
            screen.blit(self._font_label.render(label, True, _TEXT_SECONDARY), (cx + pad, y))
            screen.blit(self._font_value.render(value, True, _TEXT_PRIMARY),   (cx + pad, y + 14))
            y += 44

        def divider():
            nonlocal y
            pygame.draw.line(screen, _DIVIDER, (cx + pad, y), (cx + card_w - pad, y))
            y += 16

        def hs_row(label, score, seed, seed_attr):
            nonlocal y
            value = "—" if score is None else str(score)
            screen.blit(self._font_label.render(label, True, _TEXT_SECONDARY), (cx + pad, y))
            screen.blit(self._font_value.render(value, True, _TEXT_PRIMARY),   (cx + pad, y + 14))
            if score is not None:
                sub_x    = cx + pad + self._font_value.size(value)[0] + 10
                sub_y    = y + 18
                sub_surf = self._font_label.render(f"Seed: {seed}", True, _TEXT_SECONDARY)
                sr = pygame.Rect(sub_x - 2, sub_y - 2, sub_surf.get_width() + 4, sub_surf.get_height() + 4)
                setattr(self, seed_attr, sr)
                if sr.collidepoint(mouse):
                    pygame.draw.rect(screen, (230, 228, 222), sr, border_radius=3)
                screen.blit(sub_surf, (sub_x, sub_y))
            y += 44

        row("GAMES PLAYED", str(s["total_games"]))
        row("TIME PLAYED",  _fmt_time(s["total_time"]))
        divider()
        row("VS AI RECORD", f"{s['vs_wins']}W   {s['vs_losses']}L   {s['vs_ties']}T")
        divider()
        hs_row("BEST SCORE — RANDOM",   s["random_best"],   s["random_best_seed"],   "_random_seed_rect")
        hs_row("BEST SCORE — SOLVABLE", s["solvable_best"], s["solvable_best_seed"], "_solvable_seed_rect")

        btn_surf = self._font_btn.render("Full History", True, _TEXT_PRIMARY)
        bp_x, bp_y = 12, 6
        bw = btn_surf.get_width()  + bp_x * 2
        bh = btn_surf.get_height() + bp_y * 2
        bx = cx + (card_w - bw) // 2
        by = cy + card_h - bh - 16
        self.history_btn_rect = pygame.Rect(bx, by, bw, bh)
        hov = self.history_btn_rect.collidepoint(mouse)
        pygame.draw.rect(screen, (190, 188, 180) if hov else (210, 208, 200), self.history_btn_rect, border_radius=6)
        pygame.draw.rect(screen, (160, 158, 150), self.history_btn_rect, width=1, border_radius=6)
        screen.blit(btn_surf, (bx + bp_x, by + bp_y))

        self._draw_copied_toast(screen, cx, cy, card_w, card_h)

    # ── history view ──────────────────────────────────────────────────

    def _draw_history(self, screen):
        card_w, card_h = 520, 400
        cx, cy = self._draw_card(screen, card_w, card_h)
        mouse  = pygame.mouse.get_pos()
        pad    = 20

        title = self._font_title.render("Full History", True, _TEXT_PRIMARY)
        screen.blit(title, (cx + (card_w - title.get_width()) // 2, cy + 18))

        back_surf = self._font_btn.render("← Back", True, _TEXT_SECONDARY)
        bp_x, bp_y = 8, 6
        bw = back_surf.get_width()  + bp_x * 2
        bh = back_surf.get_height() + bp_y * 2
        self.back_btn_rect = pygame.Rect(cx + pad, cy + 16, bw, bh)
        if self.back_btn_rect.collidepoint(mouse):
            pygame.draw.rect(screen, (230, 228, 222), self.back_btn_rect, border_radius=5)
        screen.blit(back_surf, (cx + pad + bp_x, cy + 16 + bp_y))

        header_y = cy + 56
        cols = [
            (cx + pad,       "MODE"),
            (cx + pad + 90,  "GRID"),
            (cx + pad + 175, "SCORE"),
            (cx + pad + 240, "OPP"),
            (cx + pad + 305, "SEED"),
        ]
        for x, label in cols:
            screen.blit(self._font_label.render(label, True, _TEXT_SECONDARY), (x, header_y))

        hint = self._font_label.render("Click row to copy seed", True, _TEXT_SECONDARY)
        screen.blit(hint, (cx + card_w - hint.get_width() - pad, header_y + 2))

        pygame.draw.line(screen, _DIVIDER, (cx + pad, header_y + 18), (cx + card_w - pad, header_y + 18))

        row_area_y = header_y + 24
        row_area_h = card_h - (row_area_y - cy) - pad
        self._visible_rows  = max(1, row_area_h // self._row_h)
        self._row_area_rect = pygame.Rect(cx + pad, row_area_y, card_w - pad * 2, row_area_h)

        screen.set_clip(pygame.Rect(cx + pad, row_area_y, card_w - pad * 2, row_area_h))

        for i, game in enumerate(self._history[self._scroll:self._scroll + self._visible_rows]):
            ry  = row_area_y + i * self._row_h
            idx = i + self._scroll
            row_rect = pygame.Rect(cx + pad, ry, card_w - pad * 2, self._row_h)

            if idx == self._selected_row:
                bg = _ROW_SEL
            elif row_rect.collidepoint(mouse):
                bg = _ROW_HOV
            elif i % 2 == 1:
                bg = _ROW_ALT
            else:
                bg = None

            if bg:
                pygame.draw.rect(screen, bg, row_rect)

            mode  = _MODE_LABEL.get(game["gamemode"], game["gamemode"])
            grid  = game["grid_type"].capitalize()
            score = str(game["self_score"])
            opp   = str(game["opp_score"]) if game["opp_score"] is not None else "—"
            seed  = str(game["seed"])

            screen.blit(self._font_col.render(mode,  True, _TEXT_PRIMARY),   (cx + pad,       ry + 4))
            screen.blit(self._font_col.render(grid,  True, _TEXT_PRIMARY),   (cx + pad + 90,  ry + 4))
            screen.blit(self._font_col.render(score, True, _TEXT_PRIMARY),   (cx + pad + 175, ry + 4))
            screen.blit(self._font_col.render(opp,   True, _TEXT_SECONDARY), (cx + pad + 240, ry + 4))
            screen.blit(self._font_col.render(seed,  True, _TEXT_SECONDARY), (cx + pad + 305, ry + 4))

        screen.set_clip(None)

        total = len(self._history)
        if total > self._visible_rows:
            bar_h = max(20, int(row_area_h * self._visible_rows / total))
            bar_y = row_area_y + int((row_area_h - bar_h) * self._scroll / max(1, total - self._visible_rows))
            bar_x = cx + card_w - pad + 4
            pygame.draw.rect(screen, _CELL_BORDER,    (bar_x, row_area_y, 4, row_area_h), border_radius=2)
            pygame.draw.rect(screen, _TEXT_SECONDARY, (bar_x, bar_y,      4, bar_h),      border_radius=2)

        self._draw_copied_toast(screen, cx, cy, card_w, card_h)

    # ── main entry ────────────────────────────────────────────────────

    def draw(self, screen):
        if not self.visible:
            return
        self._ensure_fonts()
        if self._view == "stats":
            self._draw_stats(screen)
        else:
            self._draw_history(screen)
