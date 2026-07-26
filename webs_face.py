#!/usr/bin/env python3
"""
W.E.B.S — Jarvis-style orange HUD face (pygame)

Full-screen animated interface:
  - Pulsing orange core + rotating arcs
  - Brand title: W . E . B . S
  - Type to chat, or press W+V to talk

Run:
    python3 webs_face.py
    python3 webs_face.py --voice
    python3 webs_face.py --windowed
    python3 run_webs.py --face
"""

from __future__ import annotations

import argparse
import math
import os
import queue
import random
import sys
import threading
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Load .env
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

import pygame

from brain import Brain
from brain.event_bus import Event, EventType

# Colors — orange Jarvis palette
ORANGE = (255, 140, 0)
ORANGE_HOT = (255, 180, 60)
ORANGE_DIM = (180, 90, 20)
LIGHT = (255, 210, 150)
DEEP = (40, 16, 0)
BG = (4, 2, 0)
WHITE = (255, 255, 255)
DIM = (110, 80, 50)


def _font(size: int, bold: bool = False):
    for name in ("consolas", "dejavusansmono", "liberationmono", "couriernew"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("monospace", size, bold=bold)


class Particle:
    def __init__(self, width: int, height: int, center: tuple[int, int]):
        scale = min(width, height)
        self.center = center
        self.angle = random.uniform(0, math.tau)
        self.radius = random.uniform(scale * 0.16, scale * 0.32)
        self.speed = random.uniform(0.002, 0.01) * random.choice([-1, 1])
        self.size = random.uniform(1.2, 3.2)
        self.alpha = random.uniform(50, 170)
        self.phase = random.uniform(0, math.tau)

    def update(self, energy: float = 0.0):
        self.angle += self.speed * (1.0 + energy * 2.5)

    def pos(self):
        wobble = math.sin(self.angle * 3 + self.phase) * 8
        x = self.center[0] + math.cos(self.angle) * (self.radius + wobble)
        y = self.center[1] + math.sin(self.angle) * (self.radius + wobble)
        return x, y


class ChordTracker:
    def __init__(self, cooldown: float = 1.2):
        self.w = False
        self.v = False
        self.cooldown = cooldown
        self._last = 0.0

    def keydown(self, key) -> bool:
        if key == pygame.K_w:
            self.w = True
        elif key == pygame.K_v:
            self.v = True
        return self._fire()

    def keyup(self, key) -> None:
        if key == pygame.K_w:
            self.w = False
        elif key == pygame.K_v:
            self.v = False

    def _fire(self) -> bool:
        if not (self.w and self.v):
            return False
        now = time.time()
        if now - self._last < self.cooldown:
            return False
        self._last = now
        return True


class Face:
    def __init__(
        self,
        screen: pygame.Surface,
        width: int,
        height: int,
        enable_voice: bool = False,
    ):
        self.screen = screen
        self.W = width
        self.H = height
        self.center = (width // 2, height // 2)
        self.clock = pygame.time.Clock()

        self.FONT_TITLE = _font(68, bold=True)
        self.FONT_SUB = _font(18)
        self.FONT_CHAT = _font(22)
        self.FONT_SMALL = _font(14)
        self.FONT_HINT = _font(16)

        self.brain = Brain()
        self.event_bus = self.brain.event_bus

        self.voice = None
        self._voice_enabled = enable_voice
        self._listening = False
        if enable_voice:
            self._init_voice()

        self.status_text = "ONLINE — AWAITING COMMAND"
        self.response_lines: list[str] = []
        self.response_timer = 0
        self.pulse_boost = 0.0
        self.audio_energy = 0.0
        self._speaking = False
        self.mode = "IDLE"

        self.input_text = ""
        self.input_active = True
        self.cursor_blink = 0

        self.update_queue: queue.Queue = queue.Queue()
        self.chord = ChordTracker()

        self.particles = [
            Particle(width, height, self.center) for _ in range(140)
        ]
        self.num_bars = 40
        self.bar_phases = [random.uniform(0, math.tau) for _ in range(self.num_bars)]
        self.bar_speeds = [random.uniform(3.5, 9.0) for _ in range(self.num_bars)]
        self._scan_angle = 0.0

        self._subscribe_events()
        self.update_queue.put(("status", "W.E.B.S ONLINE"))
        self.update_queue.put(("pulse", 20))

    def _init_voice(self) -> None:
        try:
            self.brain.init_voice()
            self.voice = self.brain._voice_engine
            if self.voice and self.voice.is_available():
                print("  Voice engine: CONNECTED")
            else:
                print("  Voice engine: limited / unavailable")
        except Exception as e:
            print(f"  Voice engine: unavailable ({e})")
            self._voice_enabled = False

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe(EventType.PLANNER_TASK_START, self._on_task_start)
        self.event_bus.subscribe(EventType.COLLECTOR_SEARCHING, self._on_searching)
        self.event_bus.subscribe(EventType.BRAIN_THINKING, self._on_thinking)
        self.event_bus.subscribe(EventType.BRAIN_RESPONDING, self._on_brain_response)
        self.event_bus.subscribe(EventType.BRAIN_ERROR, self._on_brain_error)
        self.event_bus.subscribe(EventType.VOICE_SPEAKING, self._on_voice_speaking)
        self.event_bus.subscribe(EventType.VOICE_IDLE, self._on_voice_idle)

    def _on_task_start(self, event: Event) -> None:
        self.update_queue.put(("status", f"TASK: {event.data.get('task', '...')}"))
        self.update_queue.put(("mode", "THINKING"))

    def _on_searching(self, event: Event) -> None:
        self.update_queue.put(("status", f"SEARCHING: {event.data.get('query', '')}"))
        self.update_queue.put(("mode", "THINKING"))

    def _on_thinking(self, event: Event) -> None:
        self.update_queue.put(("status", "THINKING..."))
        self.update_queue.put(("mode", "THINKING"))

    def _on_brain_response(self, event: Event) -> None:
        response = event.data.get("response", "")
        self.update_queue.put(("response", response))
        self.update_queue.put(("pulse", 28))
        self.update_queue.put(("status", "READY"))
        self.update_queue.put(("mode", "IDLE"))

    def _on_brain_error(self, event: Event) -> None:
        self.update_queue.put(("status", f"ERROR: {event.data.get('error', 'unknown')}"))
        self.update_queue.put(("mode", "IDLE"))

    def _on_voice_speaking(self, event: Event) -> None:
        self.update_queue.put(("audio_energy", 1.0))
        self.update_queue.put(("mode", "SPEAKING"))

    def _on_voice_idle(self, event: Event) -> None:
        self.update_queue.put(("audio_energy", 0.0))
        self.update_queue.put(("mode", "IDLE"))

    def run(self) -> None:
        t = 0.0
        running = True
        screen = self.screen

        while running:
            dt = self.clock.tick(60) / 1000.0
            t += dt
            self._scan_angle += dt * 1.2
            self._process_updates()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RETURN:
                        self._send_input()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.key == pygame.K_F1:
                        self._toggle_voice()
                    elif self.chord.keydown(event.key):
                        self._start_listen()
                    elif event.unicode and event.unicode.isprintable():
                        if not (self.chord.w and self.chord.v):
                            self.input_text += event.unicode
                elif event.type == pygame.KEYUP:
                    self.chord.keyup(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    cx, cy = self.center
                    if math.hypot(mx - cx, my - cy) < min(self.W, self.H) * 0.12:
                        if self._voice_enabled:
                            self._start_listen()
                        elif not self.input_text.strip():
                            self.input_text = "What can you do?"
                            self._send_input()

            self._update_visuals(t)
            screen.fill(BG)
            self._draw_vignette(screen)
            self._draw_particles(screen)
            self._draw_outer_ring(screen, t)
            self._draw_arcs(screen, t)
            self._draw_hex_frame(screen, t)
            self._draw_core(screen, t)
            self._draw_scan_line(screen)
            self._draw_text(screen, t)
            self._draw_bars(screen, t)
            self._draw_response(screen)
            self._draw_chat_input(screen)
            self._draw_hud_corners(screen)
            self._draw_hints(screen)
            pygame.display.flip()

        self.brain.shutdown()
        if self.voice:
            try:
                self.voice.close()
            except Exception:
                pass
        pygame.quit()

    def _process_updates(self) -> None:
        try:
            while True:
                typ, data = self.update_queue.get_nowait()
                if typ == "status":
                    self.status_text = str(data)
                elif typ == "response":
                    self.response_lines = self._wrap_text(data, 72)
                    self.response_timer = 420
                elif typ == "pulse":
                    self.pulse_boost = float(data)
                elif typ == "audio_energy":
                    self.audio_energy = float(data)
                    self._speaking = data > 0.4
                elif typ == "mode":
                    self.mode = str(data)
        except queue.Empty:
            pass

    def _wrap_text(self, text: str, max_chars: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if len(test) <= max_chars:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    def _send_input(self) -> None:
        if not self.input_text.strip():
            return
        user_msg = self.input_text.strip()
        self.status_text = "PROCESSING..."
        self.mode = "THINKING"
        self.input_text = ""

        def process():
            try:
                reply = self.brain.process(user_msg)
                self.update_queue.put(("response", reply))
                self.update_queue.put(("pulse", 25))
                self.update_queue.put(("status", "READY"))
                self.update_queue.put(("mode", "IDLE"))
            except Exception as e:
                self.update_queue.put(("status", f"ERROR: {e}"))
                self.update_queue.put(("mode", "IDLE"))

        threading.Thread(target=process, daemon=True).start()

    def _toggle_voice(self) -> None:
        self._voice_enabled = not self._voice_enabled
        if self._voice_enabled and not self.brain._stt:
            self._init_voice()
        self.update_queue.put(("status", f"VOICE: {'ON' if self._voice_enabled else 'OFF'}"))

    def _start_listen(self) -> None:
        if self._listening:
            return
        if not self._voice_enabled:
            self.update_queue.put(("status", "VOICE OFF — press F1 or run with --voice"))
            return
        if not self.brain._stt or not self.brain._stt.available:
            self.update_queue.put(("status", "MIC UNAVAILABLE"))
            return

        self._listening = True
        self.update_queue.put(("mode", "LISTENING"))
        self.update_queue.put(("status", "LISTENING... (W+V)"))
        self.update_queue.put(("pulse", 15))

        def listen_job():
            try:
                heard = self.brain._stt.listen_once(timeout=6)
                if heard:
                    self.update_queue.put(("status", f"HEARD: {heard[:40]}"))
                    self.input_text = heard
                    self._send_input()
                else:
                    self.update_queue.put(("status", "NOTHING HEARD"))
                    self.update_queue.put(("mode", "IDLE"))
            except Exception as e:
                self.update_queue.put(("status", f"LISTEN ERROR: {e}"))
                self.update_queue.put(("mode", "IDLE"))
            finally:
                self._listening = False

        threading.Thread(target=listen_job, daemon=True).start()

    def _update_visuals(self, t: float) -> None:
        if self.pulse_boost > 0:
            self.pulse_boost = max(0.0, self.pulse_boost - 0.45)
        if self._speaking or self.mode == "SPEAKING":
            self.audio_energy = max(self.audio_energy, 0.7 + 0.3 * abs(math.sin(t * 8)))
        elif self.mode == "LISTENING":
            self.audio_energy = 0.45 + 0.25 * abs(math.sin(t * 5))
        elif self.mode == "THINKING":
            self.audio_energy = 0.25 + 0.15 * abs(math.sin(t * 3))
        else:
            self.audio_energy *= 0.93
            if self.audio_energy < 0.02:
                self.audio_energy = 0.0
        self.cursor_blink = (self.cursor_blink + 1) % 60

    def _draw_vignette(self, surface) -> None:
        vignette = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        for i in range(8):
            alpha = 18 + i * 8
            inset = i * 40
            pygame.draw.rect(
                vignette,
                (0, 0, 0, alpha),
                (inset, inset, self.W - inset * 2, self.H - inset * 2),
                width=40,
            )
        surface.blit(vignette, (0, 0))

    def _draw_glow(self, surface, color, center, radius, layers=10, max_alpha=75):
        size = int(radius * 2.8)
        glow = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        gc = (glow.get_width() // 2, glow.get_height() // 2)
        for i in range(layers, 0, -1):
            alpha = int(max_alpha * (i / layers) ** 2)
            r = int(radius * (0.55 + (layers - i) * 0.18))
            pygame.draw.circle(glow, (*color, alpha), gc, r)
        surface.blit(
            glow,
            (center[0] - gc[0], center[1] - gc[1]),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_core(self, surface, t: float) -> None:
        base = int(min(self.W, self.H) * 0.11)
        pulse = math.sin(t * 2.6) * 7
        radius = base + pulse + self.pulse_boost + self.audio_energy * 22
        self._draw_glow(surface, ORANGE, self.center, int(radius), layers=12, max_alpha=85)

        steps = 55
        for i in range(steps, 0, -1):
            frac = i / steps
            r = int(radius * frac)
            color = (
                int(DEEP[0] + (LIGHT[0] - DEEP[0]) * (1 - frac) ** 0.7),
                int(DEEP[1] + (LIGHT[1] - DEEP[1]) * (1 - frac) ** 0.7),
                int(DEEP[2] + (LIGHT[2] - DEEP[2]) * (1 - frac) ** 0.7),
            )
            pygame.draw.circle(surface, color, self.center, r)

        nucleus = int(radius * 0.28)
        pygame.draw.circle(surface, ORANGE_HOT, self.center, nucleus)
        pygame.draw.circle(surface, WHITE, self.center, max(2, nucleus // 3))

    def _draw_hex_frame(self, surface, t: float) -> None:
        r = min(self.W, self.H) * 0.145 + self.audio_energy * 8
        rot = t * 0.25
        points = [
            (
                self.center[0] + math.cos(rot + i * math.tau / 6) * r,
                self.center[1] + math.sin(rot + i * math.tau / 6) * r,
            )
            for i in range(6)
        ]
        pygame.draw.polygon(surface, ORANGE_DIM, points, width=2)
        r2 = r * 0.72
        points2 = [
            (
                self.center[0] + math.cos(-rot * 1.4 + i * math.tau / 6) * r2,
                self.center[1] + math.sin(-rot * 1.4 + i * math.tau / 6) * r2,
            )
            for i in range(6)
        ]
        pygame.draw.polygon(surface, ORANGE, points2, width=1)

    def _draw_arc_segment(self, surface, center, radius, a0, a1, color, width):
        steps = max(4, int(abs(a1 - a0) * radius / 8))
        points = []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * (i / steps)
            points.append(
                (center[0] + math.cos(a) * radius, center[1] + math.sin(a) * radius)
            )
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, width)

    def _draw_arcs(self, surface, t: float) -> None:
        scale = min(self.W, self.H)
        arcs = [
            (0.20, 0.85, 4, 0.55, ORANGE),
            (0.235, -0.55, 3, 0.35, ORANGE_HOT),
            (0.275, 0.35, 5, 0.25, ORANGE_DIM),
        ]
        for frac, speed, width, span, color in arcs:
            radius = int(scale * frac + self.audio_energy * 6)
            start = t * speed
            segments = 48
            for i in range(segments):
                if (i % 5) in (3, 4):
                    continue
                a0 = start + (i / segments) * math.tau
                a1 = a0 + (math.tau / segments) * 0.85
                self._draw_arc_segment(surface, self.center, radius, a0, a1, color, width)
            sweep = start * 2.2
            self._draw_arc_segment(
                surface, self.center, radius, sweep, sweep + span, LIGHT, width + 1
            )

    def _draw_outer_ring(self, surface, t: float) -> None:
        radius = int(min(self.W, self.H) * 0.33)
        for i in range(72):
            a = t * 0.15 + i * math.tau / 72
            inner = radius - (10 if i % 6 == 0 else 4)
            x0 = self.center[0] + math.cos(a) * inner
            y0 = self.center[1] + math.sin(a) * inner
            x1 = self.center[0] + math.cos(a) * radius
            y1 = self.center[1] + math.sin(a) * radius
            col = ORANGE if i % 6 == 0 else ORANGE_DIM
            pygame.draw.line(surface, col, (x0, y0), (x1, y1), 1)

    def _draw_scan_line(self, surface) -> None:
        radius = min(self.W, self.H) * 0.30
        a = self._scan_angle
        x = self.center[0] + math.cos(a) * radius
        y = self.center[1] + math.sin(a) * radius
        pygame.draw.line(surface, LIGHT, self.center, (x, y), 1)
        for i in range(1, 8):
            a2 = a - i * 0.04
            x2 = self.center[0] + math.cos(a2) * radius
            y2 = self.center[1] + math.sin(a2) * radius
            alpha_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            pygame.draw.line(
                alpha_surf, (*ORANGE, max(10, 80 - i * 10)), self.center, (x2, y2), 1
            )
            surface.blit(alpha_surf, (0, 0))

    def _draw_particles(self, surface) -> None:
        for p in self.particles:
            p.update(self.audio_energy)
            x, y = p.pos()
            size = p.size + self.audio_energy * 2.2
            s = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(s, (*ORANGE, int(p.alpha)), (7, 7), size)
            surface.blit(s, (x - 7, y - 7), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_text(self, surface, t: float) -> None:
        flicker = 255 if math.sin(t * 7) > -0.85 else 190
        title_color = (255, min(170, flicker), min(70, flicker // 2))
        title = self.FONT_TITLE.render("W . E . B . S", True, title_color)
        ty = self.center[1] + int(min(self.W, self.H) * 0.20)
        surface.blit(title, (self.center[0] - title.get_width() // 2, ty))

        uw = title.get_width()
        pygame.draw.line(
            surface,
            ORANGE_DIM,
            (self.center[0] - uw // 2, ty + title.get_height() + 4),
            (self.center[0] + uw // 2, ty + title.get_height() + 4),
            1,
        )

        sub = self.FONT_SUB.render(self.status_text.upper(), True, LIGHT)
        surface.blit(
            sub,
            (self.center[0] - sub.get_width() // 2, ty + title.get_height() + 16),
        )

        mode_col = {
            "IDLE": ORANGE_DIM,
            "THINKING": ORANGE_HOT,
            "LISTENING": LIGHT,
            "SPEAKING": ORANGE,
        }.get(self.mode, ORANGE)
        mode = self.FONT_SMALL.render(f"● {self.mode}", True, mode_col)
        surface.blit(
            mode,
            (
                self.center[0] - mode.get_width() // 2,
                self.center[1] - int(min(self.W, self.H) * 0.22),
            ),
        )

    def _draw_response(self, surface) -> None:
        if self.response_timer <= 0 or not self.response_lines:
            return
        self.response_timer -= 1
        alpha = min(255, self.response_timer * 2)
        x_start = 56
        y = int(self.H * 0.18)
        header = self.FONT_SMALL.render("RESPONSE", True, ORANGE)
        header.set_alpha(alpha)
        surface.blit(header, (x_start, y - 22))
        for i, line in enumerate(self.response_lines[:9]):
            text_surf = self.FONT_CHAT.render(line, True, WHITE)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (x_start, y + i * 30))

    def _draw_chat_input(self, surface) -> None:
        box_h = 48
        box_w = self.W - 120
        box_rect = pygame.Rect(60, self.H - 88, box_w, box_h)
        pygame.draw.rect(surface, (18, 8, 2), box_rect, border_radius=8)
        pygame.draw.rect(surface, ORANGE, box_rect, 2, border_radius=8)

        display = self.input_text
        if self.cursor_blink < 30 and self.input_active:
            display += "|"
        text_surf = self.FONT_CHAT.render(display, True, WHITE)
        surface.blit(text_surf, (box_rect.x + 14, box_rect.y + 10))

        if not self.input_text and self.input_active:
            hint = self.FONT_CHAT.render("Ask W.E.B.S anything…", True, DIM)
            surface.blit(hint, (box_rect.x + 14, box_rect.y + 10))

    def _draw_bars(self, surface, t: float) -> None:
        bar_w, gap = 5, 3
        total = self.num_bars * (bar_w + gap)
        start_x = self.center[0] - total // 2
        base_y = self.H - 28
        for i in range(self.num_bars):
            h = 6 + abs(math.sin(t * self.bar_speeds[i] + self.bar_phases[i])) * 26
            h += self.audio_energy * 38 * abs(math.sin(t * 3.2 + i * 0.28))
            x = start_x + i * (bar_w + gap)
            rect = pygame.Rect(x, base_y - h, bar_w, h)
            pygame.draw.rect(surface, ORANGE_HOT if h > 35 else ORANGE, rect, border_radius=2)

    def _draw_hud_corners(self, surface) -> None:
        length, thick, margin = 36, 2, 28
        c = ORANGE_DIM
        W, H = self.W, self.H
        pygame.draw.line(surface, c, (margin, margin), (margin + length, margin), thick)
        pygame.draw.line(surface, c, (margin, margin), (margin, margin + length), thick)
        pygame.draw.line(surface, c, (W - margin, margin), (W - margin - length, margin), thick)
        pygame.draw.line(surface, c, (W - margin, margin), (W - margin, margin + length), thick)
        pygame.draw.line(surface, c, (margin, H - margin), (margin + length, H - margin), thick)
        pygame.draw.line(surface, c, (margin, H - margin), (margin, H - margin - length), thick)
        pygame.draw.line(surface, c, (W - margin, H - margin), (W - margin - length, H - margin), thick)
        pygame.draw.line(surface, c, (W - margin, H - margin), (W - margin, H - margin - length), thick)
        brand = self.FONT_SMALL.render("W.E.B.S  //  AI INTERFACE", True, ORANGE_DIM)
        surface.blit(brand, (margin + 8, margin + 8))

    def _draw_hints(self, surface) -> None:
        lines = [
            "ENTER  send",
            "W+V    talk" if self._voice_enabled else "F1     voice",
            "ESC    exit",
        ]
        y = 28
        for line in lines:
            surf = self.FONT_HINT.render(line, True, DIM)
            surface.blit(surf, (self.W - surf.get_width() - 36, y))
            y += 22


def main() -> None:
    parser = argparse.ArgumentParser(description="W.E.B.S Face — Jarvis HUD")
    parser.add_argument("--voice", action="store_true", help="Enable voice (W+V to talk)")
    parser.add_argument("--windowed", action="store_true", help="Windowed instead of fullscreen")
    args = parser.parse_args()

    pygame.init()
    info = pygame.display.Info()
    if args.windowed:
        width, height = 1280, 800
        flags = 0
    else:
        width, height = info.current_w, info.current_h
        flags = pygame.FULLSCREEN

    screen = pygame.display.set_mode((width, height), flags)
    pygame.display.set_caption("W.E.B.S")

    print("=" * 60)
    print("  W . E . B . S  —  AI Operating System")
    print("  Orange Jarvis Interface")
    print("=" * 60)
    print(f"  Resolution: {width}x{height}")
    print(f"  Voice: {'Enabled (W+V)' if args.voice else 'Disabled (F1 to toggle)'}")
    print("  ESC to exit")

    face = Face(screen, width, height, enable_voice=args.voice)
    face.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
