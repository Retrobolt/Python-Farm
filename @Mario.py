#!/usr/bin/env python3
"""
ASCII Mario Platformer - Terminal game using curses
Run:  python "@Mario.py"
      python "@Mario.py" --debug
Windows: pip install windows-curses first
"""

import curses
import time
import sys
import argparse

# ── Constants ────────────────────────────────────────────────────────────────
FPS         = 60
GRAVITY     = 0.055        # tiles/frame²
MAX_FALL    = 1.0          # tiles/frame (terminal velocity)
WALK_SPEED  = 0.28         # tiles/frame
RUN_SPEED   = 0.50         # tiles/frame
WALK_ACCEL  = 0.07         # acceleration per frame
FRICTION    = 0.78         # velocity multiplier when no input
JUMP_VEL    = -0.72        # tiles/frame upward
JUMP_HOLD   = 18           # max frames jump key held for extra height
JUMP_BOOST  = 0.022        # extra upward acceleration per hold frame
COYOTE_TIME = 4            # frames
JUMP_BUFFER = 4            # frames

TILE_W = 2                 # screen columns per tile
TILE_H = 1                 # screen rows per tile

# Color pair IDs
C_MARIO  = 1
C_ENEMY  = 2
C_BLOCK  = 3
C_PIPE   = 4
C_COIN   = 5
C_SKY    = 6
C_GROUND = 7
C_HUD    = 8
C_ITEM   = 9
C_CASTLE = 10
C_FLAG   = 11

DEBUG: bool = False

# ── Level map ────────────────────────────────────────────────────────────────
# 16 rows × 110 columns.  Ground row = 13.  Mario starts at x=2, y=12.
# Char key:
#   ' '  air        '='  ground      '#'  brick
#   '?'  ? block    'b'  empty block 'T'  pipe top
#   '|'  pipe body  'G'  goomba      'K'  koopa
#   'C'  coin       'F'  flagpole    'X'  castle wall
LEVEL_MAP = [
#   0         1         2         3         4         5         6         7         8         9         10
#   0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
    "                                                                                                             C        ",# 0
    "                                                                                                                      ",# 1
    "                                                                                                                      ",# 2
    "                                                 C  C  C                                                             ",# 3
    "                       ?   ?#?                                  ?                                                    ",# 4
    "                                                                                                                      ",# 5
    "                  #  #                                    ####                                                        ",# 6
    "                                                                                                                      ",# 7
    "                                                                                                                      ",# 8
    "                                                                                                                      ",# 9
    "                                                                                                                      ",# 10
    "                                                                                                                      ",# 11
    "                                                                                                                      ",# 12
    "==       G       T  =======     G  G  =======     K     T  ===========================  T  ==========  F            ",# 13
    "==       ======= |            ======  =======           |  ===========================  |  ==========  |  X         ",# 14
    "=========        |            ======  =======           |  ===========================  |  ==========  |  X         ",# 15
]

LEVEL_W = len(LEVEL_MAP[0])
LEVEL_H = len(LEVEL_MAP)
GROUND_ROW = 13   # main floor row

# Mutable active map — updated on level reset so tile_at() sees block changes
_active_level: list[list[str]] = [list(row) for row in LEVEL_MAP]

# Tile classifications
SOLID_TILES = set("=#?TbX")   # 'b' = spent block (still solid)


def tile_at(tx: int, ty: int) -> str:
    if ty < 0 or ty >= LEVEL_H or tx < 0 or tx >= LEVEL_W:
        return ' '
    return _active_level[ty][tx]


def is_solid(tx: int, ty: int) -> bool:
    return tile_at(tx, ty) in SOLID_TILES


# ── Sprites ───────────────────────────────────────────────────────────────────
SPRITE_MARIO_SMALL  = [" o ", "/|\\"]
SPRITE_MARIO_BIG    = ["\\o/", "-|-", "/ \\"]
SPRITE_MARIO_DEAD   = [" o ", "---"]
SPRITE_GOOMBA       = ["(oo)", " )( "]
SPRITE_KOOPA        = ["{@@}", " )( "]
SPRITE_SHELL        = ["[  ]"]
SPRITE_MUSHROOM     = [" ^ ", "(M)"]
SPRITE_FLOWER       = [" * ", "(F)"]
SPRITE_STAR         = [" * ", "***"]
SPRITE_1UP          = [" ^ ", "(1)"]
SPRITE_COIN_POP     = [" C "]


# ── InputHandler ─────────────────────────────────────────────────────────────
class InputHandler:
    """
    Tracks held-state via key-age (frames since last seen).

    Terminals don't send key-UP events.  Instead a held key generates:
      • one event on press
      • a ~500 ms silence (the key-repeat DELAY)
      • repeated events every ~30 ms thereafter

    So the timeout per key type must be long enough to survive the initial
    silence, otherwise the key appears "released" before repeat kicks in:

      MOVE_TIMEOUT  ≥ 500 ms ≈ 30 frames  → use 50 for safety
      JUMP_TIMEOUT  shorter so releasing jump early cuts the jump arc
    """
    # frames without a repeat event before the key is considered released
    _TIMEOUT: dict[str, int] = {
        'left': 50, 'right': 50, 'down': 50, 'run': 50,
        'jump': 20,
        'up': 50, 'enter': 10, 'quit': 10,
    }
    _DEFAULT_TIMEOUT = 10

    KEY_MAP: dict[int, str] = {}   # built lazily after curses is up

    def __init__(self):
        self._age: dict[str, int] = {}
        self.held:         set[str] = set()
        self.just_pressed: set[str] = set()

    def _build_keymap(self):
        self.KEY_MAP = {
            curses.KEY_LEFT:  'left',
            curses.KEY_RIGHT: 'right',
            curses.KEY_UP:    'up',
            curses.KEY_DOWN:  'down',
            ord('z'):  'jump',   ord('Z'):  'jump',
            ord(' '):  'jump',
            ord('x'):  'run',    ord('X'):  'run',
            ord('\n'): 'enter',  ord('\r'): 'enter',
            ord('p'):  'enter',  ord('P'):  'enter',
            ord('q'):  'quit',   ord('Q'):  'quit',
        }

    def update(self, stdscr: "curses._CursesWindow"):
        if not self.KEY_MAP:
            self._build_keymap()

        for k in list(self._age):
            self._age[k] += 1

        seen: set[str] = set()
        while True:
            ch = stdscr.getch()
            if ch == -1:
                break
            name = self.KEY_MAP.get(ch)
            if name:
                seen.add(name)

        self.just_pressed = set()
        for name in seen:
            timeout = self._TIMEOUT.get(name, self._DEFAULT_TIMEOUT)
            old_age = self._age.get(name, 999)
            self._age[name] = 0
            if old_age > timeout:
                self.just_pressed.add(name)

        self.held = {
            k for k, age in self._age.items()
            if age <= self._TIMEOUT.get(k, self._DEFAULT_TIMEOUT)
        }

    def is_held(self, name: str) -> bool:
        return name in self.held

    def was_pressed(self, name: str) -> bool:
        return name in self.just_pressed


# ── Mario ─────────────────────────────────────────────────────────────────────
class Mario:
    def __init__(self, tx: float, ty: float):
        self.x   = float(tx)
        self.y   = float(ty)   # y of feet (bottom of sprite body)
        self.vx  = 0.0
        self.vy  = 0.0

        self.on_ground      = False
        self.coyote_timer   = 0
        self.jump_buffer    = 0
        self.jump_hold_cnt  = 0
        self.is_jumping     = False

        self.size  = 'small'   # 'small' | 'super' | 'fire'
        self.state = 'idle'
        self.facing = 1

        self.dead       = False
        self.dead_vy    = 0.0
        self.dead_timer = 0

        self.invincible  = 0   # frames
        self.grow_timer  = 0

        self.score = 0
        self.coins = 0
        self.lives = 3

        self.anim_frame = 0
        self.anim_tick  = 0

    @property
    def h(self) -> int:
        """Sprite/hitbox height in tiles."""
        return 2 if self.size == 'small' else 3

    def hitbox(self) -> tuple[float, float, float, float]:
        """(left, top, right, bottom) — bottom is the feet row + 1."""
        return (self.x, self.y - self.h + 1, self.x + 1.0, self.y + 1.0)

    def sprite(self) -> list[str]:
        if self.dead:
            return SPRITE_MARIO_DEAD
        return SPRITE_MARIO_SMALL if self.size == 'small' else SPRITE_MARIO_BIG

    # ── Main update ──────────────────────────────────────────────────────────
    def update(self, inp: InputHandler, events: list):
        if self.dead:
            self._update_dead()
            return

        if self.invincible > 0:
            self.invincible -= 1
        if self.grow_timer > 0:
            self.grow_timer -= 1

        # Coyote time
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        # Jump buffer
        if inp.was_pressed('jump'):
            self.jump_buffer = JUMP_BUFFER
        elif self.jump_buffer > 0:
            self.jump_buffer -= 1

        crouching = inp.is_held('down') and self.on_ground and self.size != 'small'

        # ── Horizontal ───────────────────────────────────────────────────────
        if not crouching:
            running = inp.is_held('run')
            top_spd = RUN_SPEED if running else WALK_SPEED
            if inp.is_held('left'):
                self.vx = max(self.vx - WALK_ACCEL, -top_spd)
                self.facing = -1
            elif inp.is_held('right'):
                self.vx = min(self.vx + WALK_ACCEL, top_spd)
                self.facing = 1
            else:
                self.vx *= FRICTION
                if abs(self.vx) < 0.005:
                    self.vx = 0.0
        else:
            self.vx *= 0.6

        # ── Jump ─────────────────────────────────────────────────────────────
        if self.coyote_timer > 0 and self.jump_buffer > 0 and not self.is_jumping:
            self.vy = JUMP_VEL
            self.is_jumping   = True
            self.jump_hold_cnt = 0
            self.jump_buffer  = 0
            self.coyote_timer = 0

        # Variable height: holding jump adds extra upward push
        if self.is_jumping and inp.is_held('jump') and self.vy < 0:
            self.jump_hold_cnt += 1
            if self.jump_hold_cnt <= JUMP_HOLD:
                self.vy -= JUMP_BOOST
        if self.vy >= 0:
            self.is_jumping = False

        # ── Gravity ──────────────────────────────────────────────────────────
        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        # ── Move & collide (X then Y) ─────────────────────────────────────
        self.x += self.vx
        self._collide_x()
        self.x = max(0.0, self.x)   # left-wall clamp

        self.y += self.vy
        self._collide_y(events)

        # Fell off bottom → die
        if self.y > LEVEL_H + 2:
            self.die()

        # ── Animation state ───────────────────────────────────────────────
        if crouching:
            self.state = 'crouch'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        elif abs(self.vx) < 0.01:
            self.state = 'idle'
        elif abs(self.vx) >= RUN_SPEED * 0.9:
            self.state = 'run'
        else:
            self.state = 'walk'

        self.anim_tick += 1
        if self.anim_tick >= 8:
            self.anim_tick  = 0
            self.anim_frame = (self.anim_frame + 1) % 4

    def _update_dead(self):
        self.dead_timer += 1
        if self.dead_timer > 15:
            self.dead_vy = min(self.dead_vy + GRAVITY * 2, MAX_FALL * 2)
            self.y += self.dead_vy

    def _collide_x(self):
        """Push Mario out of walls horizontally.
        Only checks BODY rows (top .. foot-row exclusive) so ground tiles
        don't push him sideways."""
        left, top, right, bottom = self.hitbox()
        # Foot row = int(bottom - epsilon); body rows are strictly above it.
        foot_row = int(bottom - 0.001)
        row_top  = int(top)

        for ty in range(row_top, foot_row):   # excludes foot row
            if is_solid(int(left), ty):
                self.x = float(int(left) + 1)
                self.vx = 0.0
                return
            if is_solid(int(right - 0.001), ty):
                self.x = float(int(right - 0.001)) - 1.0
                self.vx = 0.0
                return

    def _collide_y(self, events: list):
        self.on_ground = False
        left, top, right, bottom = self.hitbox()

        if self.vy >= 0:   # moving down
            ty = int(bottom)
            for tx in range(int(left), int(right - 0.001) + 1):
                if is_solid(tx, ty):
                    self.y      = float(ty) - 1.0   # feet sit just above tile
                    self.vy     = 0.0
                    self.on_ground  = True
                    self.is_jumping = False
                    return
        else:              # moving up
            ty = int(top)
            for tx in range(int(left), int(right - 0.001) + 1):
                if tile_at(tx, ty) in SOLID_TILES:
                    self.y  = float(ty) + float(self.h)   # head pushed below tile
                    self.vy = 0.0
                    events.append(('block_hit', tx, ty))
                    return

    def collect_coin(self):
        self.coins += 1
        self.score += 200
        if self.coins >= 100:
            self.coins = 0
            self.lives += 1

    def grow(self):
        if self.size == 'small':
            self.size = 'super'
        elif self.size == 'super':
            self.size = 'fire'
        self.grow_timer = 40

    def shrink(self):
        if self.invincible > 0:
            return
        if self.size != 'small':
            self.size = 'small'
            self.invincible = 120
        else:
            self.die()

    def die(self):
        if self.invincible > 0:
            return
        self.dead      = True
        self.dead_vy   = -0.8
        self.dead_timer = 0
        self.lives     -= 1


# ── Enemy ─────────────────────────────────────────────────────────────────────
class Enemy:
    WALK_SPEED = 0.05   # tiles/frame

    def __init__(self, tx: float, ty: float):
        self.x   = float(tx)
        self.y   = float(ty)
        self.vx  = -self.WALK_SPEED
        self.vy  = 0.0
        self.alive     = True
        self.dead      = False
        self.dead_timer = 0

    def hitbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y - 1.0, self.x + 1.0, self.y + 1.0)

    def update(self):
        if not self.alive:
            self.dead_timer += 1
            return

        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        self.x += self.vx
        self.y += self.vy
        self._collide()

    def _collide(self):
        left, _, right, bottom = self.hitbox()
        ty = int(bottom)

        # Floor
        on_floor = False
        for tx in range(int(left), int(right - 0.001) + 1):
            if is_solid(tx, ty):
                self.y  = float(ty) - 1.0
                self.vy = 0.0
                on_floor = True
                break

        if not on_floor:
            return

        # Wall check
        if self.vx > 0:
            tx_front = int(right + 0.1)
        else:
            tx_front = int(left - 0.1)
        if is_solid(tx_front, int(self.y)):
            self.vx = -self.vx
            return

        # Ledge check — don't walk off edges
        if self.vx > 0:
            tx_edge = int(right + 0.05)
        else:
            tx_edge = int(left - 0.05)
        if not is_solid(tx_edge, ty):
            self.vx = -self.vx

    def stomp(self, *_):
        pass

    def sprite(self) -> list[str]:
        return SPRITE_GOOMBA


class Goomba(Enemy):
    def stomp(self, mario: Mario):
        self.alive = False
        self.dead  = True
        mario.score += 100
        mario.vy = -0.45   # small bounce

    def sprite(self) -> list[str]:
        return ["----"] if self.dead else SPRITE_GOOMBA


class Koopa(Enemy):
    def __init__(self, tx: float, ty: float):
        super().__init__(tx, ty)
        self.shelled = False

    def stomp(self, mario: Mario):
        if not self.shelled:
            self.shelled = True
            self.vx = 0.0
            mario.score += 100
        else:
            self.vx = 0.18 if mario.x < self.x else -0.18
            mario.score += 100
        mario.vy = -0.45

    def sprite(self) -> list[str]:
        return SPRITE_SHELL if self.shelled else SPRITE_KOOPA


# ── Item ──────────────────────────────────────────────────────────────────────
class Item:
    def __init__(self, tx: float, ty: float, kind: str):
        self.x    = float(tx)
        self.y    = float(ty)
        self.vx   = 0.08
        self.vy   = 0.0
        self.kind = kind   # 'mushroom' | 'flower' | 'star' | '1up' | 'coin'
        self.alive = True
        # Coin pop animation
        self.pop_timer = 0
        self.pop_y     = float(ty)

    def hitbox(self) -> tuple[float, float, float, float]:
        return (self.x, self.y - 1.0, self.x + 1.0, self.y + 1.0)

    def update(self):
        if self.kind == 'coin':
            self.pop_timer += 1
            self.pop_y -= 0.15
            if self.pop_timer > 30:
                self.alive = False
            return

        if not self.alive:
            return

        if self.kind != 'flower':
            self.vy = min(self.vy + GRAVITY * 0.6, MAX_FALL)

        if self.kind == 'star' and self.vy > 0.3:
            self.vy = -0.6   # bounce

        self.x += self.vx
        self.y += self.vy
        self._collide()

    def _collide(self):
        left, _, right, bottom = self.hitbox()
        ty = int(bottom)
        for tx in range(int(left), int(right - 0.001) + 1):
            if is_solid(tx, ty):
                self.y  = float(ty) - 1.0
                self.vy = 0.0
                break
        if self.vx != 0:
            tx_front = int(right + 0.05) if self.vx > 0 else int(left - 0.05)
            if is_solid(tx_front, int(self.y)):
                self.vx = -self.vx

    def sprite(self) -> list[str]:
        if self.kind == 'mushroom': return SPRITE_MUSHROOM
        if self.kind == 'flower':   return SPRITE_FLOWER
        if self.kind == 'star':     return SPRITE_STAR
        if self.kind == '1up':      return SPRITE_1UP
        return SPRITE_COIN_POP


# ── Renderer ──────────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, stdscr: "curses._CursesWindow"):
        self.stdscr = stdscr
        self.h, self.w = stdscr.getmaxyx()
        self._init_colors()

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(C_MARIO,  curses.COLOR_WHITE,  curses.COLOR_RED)
        curses.init_pair(C_ENEMY,  curses.COLOR_WHITE,  curses.COLOR_RED)
        curses.init_pair(C_BLOCK,  curses.COLOR_BLACK,  curses.COLOR_YELLOW)
        curses.init_pair(C_PIPE,   curses.COLOR_BLACK,  curses.COLOR_GREEN)
        curses.init_pair(C_COIN,   curses.COLOR_YELLOW, curses.COLOR_BLUE)
        curses.init_pair(C_SKY,    curses.COLOR_WHITE,  curses.COLOR_BLUE)
        curses.init_pair(C_GROUND, curses.COLOR_BLACK,  curses.COLOR_WHITE)
        curses.init_pair(C_HUD,    curses.COLOR_BLACK,  curses.COLOR_WHITE)
        curses.init_pair(C_ITEM,   curses.COLOR_GREEN,  curses.COLOR_BLUE)
        curses.init_pair(C_CASTLE, curses.COLOR_WHITE,  curses.COLOR_BLACK)
        curses.init_pair(C_FLAG,   curses.COLOR_WHITE,  curses.COLOR_BLUE)

    def resize(self):
        self.h, self.w = self.stdscr.getmaxyx()

    def addstr(self, y: int, x: int, s: str, attr: int = 0):
        """Safe addstr — silently clips."""
        if y < 0 or y >= self.h - 1 or x >= self.w or not s:
            return
        if x < 0:
            s = s[-x:]
            x = 0
        if not s:
            return
        if x + len(s) > self.w:
            s = s[:self.w - x]
        if not s:
            return
        try:
            self.stdscr.addstr(y, x, s, attr)
        except curses.error:
            pass

    # ── HUD ──────────────────────────────────────────────────────────────────
    def draw_hud(self, mario: Mario, world: str, timer: int):
        hud = (f" MARIO  SCORE:{mario.score:06d}  COINS:{mario.coins:02d}"
               f"  WORLD:{world}  TIME:{timer:03d}  LIVES:{mario.lives} ")
        self.addstr(0, 0, hud.ljust(self.w), curses.color_pair(C_HUD) | curses.A_BOLD)

    # ── Tiles ─────────────────────────────────────────────────────────────────
    def draw_tile(self, ch: str, sx: int, sy: int):
        sky  = curses.color_pair(C_SKY)
        if ch == ' ':
            self.addstr(sy, sx, '  ', sky)
        elif ch == '=':
            self.addstr(sy, sx, '==', curses.color_pair(C_GROUND) | curses.A_BOLD)
        elif ch == '#':
            self.addstr(sy, sx, '[#', curses.color_pair(C_BLOCK) | curses.A_BOLD)
        elif ch == '?':
            self.addstr(sy, sx, '[?', curses.color_pair(C_BLOCK) | curses.A_BOLD | curses.A_BLINK)
        elif ch == 'b':
            self.addstr(sy, sx, '[ ', curses.color_pair(C_BLOCK))
        elif ch == 'T':
            self.addstr(sy, sx, '|T', curses.color_pair(C_PIPE) | curses.A_BOLD)
        elif ch == '|':
            self.addstr(sy, sx, '| ', curses.color_pair(C_PIPE) | curses.A_BOLD)
        elif ch == 'X':
            self.addstr(sy, sx, 'XX', curses.color_pair(C_CASTLE) | curses.A_BOLD)
        elif ch == 'F':
            self.addstr(sy, sx, ' F', curses.color_pair(C_FLAG) | curses.A_BOLD)
        elif ch == 'C':
            self.addstr(sy, sx, ' c', curses.color_pair(C_COIN) | curses.A_BOLD)
        else:
            self.addstr(sy, sx, '  ', sky)

    def draw_level(self, cam_x: int):
        play_h = self.h - 1
        n_tiles = self.w // TILE_W + 2
        t0 = cam_x // TILE_W

        for row in range(play_h):
            ty = row
            sy = row + 1   # +1 for HUD row
            for i in range(n_tiles):
                tx = t0 + i
                sx = tx * TILE_W - cam_x
                if ty >= LEVEL_H:
                    self.addstr(sy, sx, '  ', curses.color_pair(C_SKY))
                    continue
                ch = tile_at(tx, ty)
                if ch in ('G', 'K'):   # spawn markers rendered as sky
                    ch = ' '
                self.draw_tile(ch, sx, sy)

    # ── Sprites ───────────────────────────────────────────────────────────────
    def draw_sprite(self, sprite: list[str], tx: float, ty: float,
                    cam_x: int, color_id: int):
        attr = curses.color_pair(color_id) | curses.A_BOLD
        h = len(sprite)
        for i, row in enumerate(sprite):
            sy = int(ty) - h + 1 + i + 1   # +1 for HUD
            sx = int(tx) * TILE_W - cam_x
            self.addstr(sy, sx, row, attr)

    # ── Debug overlay ─────────────────────────────────────────────────────────
    def draw_debug(self, mario: Mario, fps: float, cam_x: int):
        info = (f" FPS:{fps:4.0f}  x:{mario.x:5.2f} y:{mario.y:5.2f}"
                f"  vx:{mario.vx:+.3f} vy:{mario.vy:+.3f}"
                f"  {mario.state:6}  {mario.size}  gnd:{mario.on_ground} ")
        self.addstr(1, 0, info, curses.color_pair(C_HUD))
        # Hitbox outline
        lft, top, rgt, bot = mario.hitbox()
        for iy in range(int(top), int(bot) + 1):
            self.addstr(iy + 1, int(lft) * TILE_W - cam_x - 1,
                        '|', curses.A_REVERSE)
            self.addstr(iy + 1, int(rgt) * TILE_W - cam_x,
                        '|', curses.A_REVERSE)


# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, stdscr: "curses._CursesWindow"):
        self.stdscr   = stdscr
        self.renderer = Renderer(stdscr)
        self.inp      = InputHandler()
        self.state    = 'title'
        self.world    = '1-1'
        self.timer    = 400
        self.timer_tick = 0
        self.cam_x    = 0   # camera x offset in screen pixels
        self._reset_level()

    # ── Level setup ──────────────────────────────────────────────────────────
    def _reset_level(self):
        global _active_level
        _active_level  = [list(row) for row in LEVEL_MAP]
        self.entities: list[Enemy] = []
        self.items:    list[Item]  = []
        self.events:   list        = []
        self.timer     = 400
        self.timer_tick = 0
        self.cam_x     = 0

        # Spawn entities from level map markers
        for ty, row in enumerate(LEVEL_MAP):
            for tx, ch in enumerate(row):
                if ch == 'G':
                    self.entities.append(Goomba(float(tx), float(ty)))
                elif ch == 'K':
                    self.entities.append(Koopa(float(tx), float(ty)))

        # Mario starts just left of centre, standing on ground
        self.mario = Mario(2.0, float(GROUND_ROW) - 1.0)

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        stdscr = self.stdscr
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.curs_set(0)

        frame_time = 1.0 / FPS
        last       = time.perf_counter()
        accum      = 0.0
        fps_frames = 0
        fps_elapsed = 0.0
        fps_display = 0.0

        while True:
            now     = time.perf_counter()
            elapsed = now - last
            last    = now
            accum       += elapsed
            fps_elapsed += elapsed
            fps_frames  += 1
            if fps_elapsed >= 1.0:
                fps_display = fps_frames / fps_elapsed
                fps_frames  = 0
                fps_elapsed = 0.0

            self.inp.update(stdscr)
            if self.inp.was_pressed('quit'):
                break

            while accum >= frame_time:
                self.update()
                accum -= frame_time

            self.renderer.resize()
            self.render(fps_display)
            stdscr.refresh()

            sleep = frame_time - (time.perf_counter() - now)
            if sleep > 0.001:
                time.sleep(sleep)

    # ── State machine ─────────────────────────────────────────────────────────
    def update(self):
        if self.state == 'title':
            if self.inp.was_pressed('enter') or self.inp.was_pressed('jump'):
                self.state = 'playing'
        elif self.state == 'playing':
            self._update_playing()
        elif self.state == 'paused':
            if self.inp.was_pressed('enter') or self.inp.was_pressed('jump'):
                self.state = 'playing'
        elif self.state == 'gameover':
            if self.inp.was_pressed('enter') or self.inp.was_pressed('jump'):
                self.mario.score = 0
                self.mario.coins = 0
                self.mario.lives = 3
                self._reset_level()
                self.state = 'playing'
        elif self.state == 'levelcomplete':
            if self.inp.was_pressed('enter') or self.inp.was_pressed('jump'):
                self._reset_level()
                self.state = 'playing'

    def _update_playing(self):
        if self.inp.was_pressed('enter'):
            self.state = 'paused'
            return

        # Countdown timer
        self.timer_tick += 1
        if self.timer_tick >= FPS:
            self.timer_tick = 0
            if self.timer > 0:
                self.timer -= 1
            else:
                self.mario.die()

        self.events.clear()

        # Update actors
        self.mario.update(self.inp, self.events)
        for e in self.entities:
            e.update()
        for it in self.items:
            it.update()

        # Process block-hit events
        for ev in self.events:
            if ev[0] == 'block_hit':
                self._handle_block_hit(ev[1], ev[2])

        mario = self.mario

        # Enemy ↔ Mario
        if not mario.dead:
            for e in self.entities:
                if not e.alive:
                    continue
                if self._overlaps(mario.hitbox(), e.hitbox()):
                    # Stomp: Mario falling and feet above enemy centre
                    if mario.vy > 0 and mario.y < e.y:
                        e.stomp(mario)
                    elif mario.invincible == 0:
                        mario.shrink()

        # Item ↔ Mario
        if not mario.dead:
            for it in self.items:
                if not it.alive:
                    continue
                if it.kind == 'coin':
                    coin_hb = (it.x, it.pop_y - 1, it.x + 1, it.pop_y + 1)
                    if self._overlaps(mario.hitbox(), coin_hb):
                        mario.collect_coin()
                        it.alive = False
                    continue
                if self._overlaps(mario.hitbox(), it.hitbox()):
                    self._apply_item(it)
                    it.alive = False

        # Coin tiles in level map
        ml, mt, mr, mb = mario.hitbox()
        for ty in range(int(mt), int(mb) + 1):
            for tx in range(int(ml), int(mr - 0.001) + 1):
                if tile_at(tx, ty) == 'C' and 0 <= ty < LEVEL_H and 0 <= tx < LEVEL_W:
                    _active_level[ty][tx] = ' '
                    mario.collect_coin()
                    self.items.append(Item(float(tx), float(ty), 'coin'))

        # Flagpole
        ml, mt, mr, mb = mario.hitbox()
        for ty in range(int(mt), int(mb) + 1):
            for tx in range(int(ml), int(mr - 0.001) + 1):
                if tile_at(tx, ty) == 'F':
                    height_bonus = max(0, (LEVEL_H - ty) * 500)
                    mario.score += 1000 + height_bonus
                    self.state = 'levelcomplete'

        # Clean up
        self.entities = [e for e in self.entities if not (e.dead and e.dead_timer > 30)]
        self.items    = [it for it in self.items if it.alive]

        # Camera: smooth follow, clamped
        target = int(mario.x) * TILE_W - self.renderer.w // 2
        max_cam = LEVEL_W * TILE_W - self.renderer.w
        target  = max(0, min(target, max(0, max_cam)))
        self.cam_x += int((target - self.cam_x) * 0.12) or (1 if target > self.cam_x else -1 if target < self.cam_x else 0)
        self.cam_x  = max(0, self.cam_x)

        # Death handling
        if mario.dead and mario.dead_timer > 90:
            if mario.lives <= 0:
                self.state = 'gameover'
            else:
                self._reset_level()

    # ── Block hit logic ───────────────────────────────────────────────────────
    def _handle_block_hit(self, tx: int, ty: int):
        ch = tile_at(tx, ty)
        mario = self.mario
        if ch == '?':
            _active_level[ty][tx] = 'b'
            kind = 'mushroom' if mario.size == 'small' else 'flower'
            it = Item(float(tx), float(ty - 1), kind)
            it.vy = -0.3   # pop upward
            self.items.append(it)
            mario.score += 50
        elif ch == '#':
            if mario.size != 'small':
                _active_level[ty][tx] = ' '
                mario.score += 50
            # Small Mario just bounces (velocity already zeroed by collision)

    def _apply_item(self, it: Item):
        mario = self.mario
        if it.kind in ('mushroom', '1up'):
            mario.grow() if it.kind == 'mushroom' else setattr(mario, 'lives', mario.lives + 1)
            mario.score += 1000
        elif it.kind == 'flower':
            mario.grow()
            mario.score += 1000
        elif it.kind == 'star':
            mario.invincible = 600
            mario.score += 1000

    @staticmethod
    def _overlaps(a: tuple, b: tuple) -> bool:
        al, at, ar, ab = a
        bl, bt, br, bb = b
        return al < br and ar > bl and at < bb and ab > bt

    # ── Rendering ─────────────────────────────────────────────────────────────
    def render(self, fps: float):
        self.stdscr.erase()

        if self.state == 'title':
            self._render_title()
        elif self.state in ('playing', 'paused'):
            self._render_game(fps)
            if self.state == 'paused':
                self._render_overlay("  PAUSED  ",
                                     "  ENTER: resume   Q: quit  ")
        elif self.state == 'gameover':
            self._render_game(fps)
            self._render_overlay("  GAME OVER  ",
                                 "  ENTER: restart   Q: quit  ")
        elif self.state == 'levelcomplete':
            self._render_game(fps)
            self._render_overlay(
                "  LEVEL CLEAR!  ",
                f"  SCORE: {self.mario.score}   ENTER: continue  ")

    def _render_title(self):
        rdr = self.renderer
        sky = curses.color_pair(C_SKY)
        for y in range(rdr.h - 1):
            rdr.addstr(y, 0, ' ' * rdr.w, sky)
        lines = [
            r" ____  _  _  ____  ____  ____     __  __    __    ____  ____  __  ",
            r"/ ___)/ )( \(  _ \(  __)(  _ \   (  )(  )  / \  (  _ \(  _ )/  \ ",
            r"\___ \) \/ ( ) __/ ) _)  )   /    )( / (_/\/ _ \ )   / )   /(  O )",
            r"(____/\____/(__)  (____)(__\_)   (__)\____/_/ \_/(__\_)(__\_) \__/ ",
            "",
            "            ASCII Platformer  -  Python + curses",
            "",
            "  Arrow keys: move   Z / Space: jump   X: run   P / Enter: pause",
            "",
            "             >>> PRESS ENTER OR SPACE TO START <<<",
        ]
        cy = rdr.h // 2 - len(lines) // 2
        attr = sky | curses.A_BOLD
        for i, line in enumerate(lines):
            rdr.addstr(cy + i, max(0, (rdr.w - len(line)) // 2), line, attr)

    def _render_game(self, fps: float):
        rdr   = self.renderer
        mario = self.mario
        cam   = self.cam_x

        # Sky fill
        sky_attr = curses.color_pair(C_SKY)
        for y in range(1, rdr.h - 1):
            rdr.addstr(y, 0, ' ' * rdr.w, sky_attr)

        rdr.draw_level(cam)

        # Coin pops
        for it in self.items:
            if it.kind == 'coin':
                sy = int(it.pop_y) + 1
                sx = int(it.x) * TILE_W - cam
                rdr.addstr(sy, sx, ' C ', curses.color_pair(C_COIN) | curses.A_BOLD)

        # Enemies
        for e in self.entities:
            rdr.draw_sprite(e.sprite(), e.x, e.y, cam, C_ENEMY)

        # Items (non-coin)
        for it in self.items:
            if it.kind != 'coin':
                rdr.draw_sprite(it.sprite(), it.x, it.y, cam, C_ITEM)

        # Mario (flicker when invincible)
        flicker = mario.invincible > 0 and (mario.invincible % 6) < 3
        if not flicker:
            rdr.draw_sprite(mario.sprite(), mario.x, mario.y, cam, C_MARIO)

        rdr.draw_hud(mario, self.world, self.timer)

        if DEBUG:
            rdr.draw_debug(mario, fps, cam)

    def _render_overlay(self, title: str, sub: str):
        rdr  = self.renderer
        cy   = rdr.h // 2
        cx   = rdr.w  // 2
        w    = max(len(title), len(sub)) + 4
        attr = curses.color_pair(C_HUD) | curses.A_BOLD
        rdr.addstr(cy - 2, cx - w // 2, '=' * w,           attr)
        rdr.addstr(cy - 1, cx - w // 2, title.center(w),   attr)
        rdr.addstr(cy,     cx - w // 2, sub.center(w),     attr)
        rdr.addstr(cy + 1, cx - w // 2, '=' * w,           attr)


# ── Entry point ───────────────────────────────────────────────────────────────
def main(stdscr: "curses._CursesWindow"):
    Game(stdscr).run()


if __name__ == '__main__':
    if sys.platform == 'win32':
        print("Windows: install windows-curses first:  pip install windows-curses")

    parser = argparse.ArgumentParser(description='ASCII Mario Platformer')
    parser.add_argument('--debug', action='store_true', help='Debug overlay')
    DEBUG = parser.parse_args().debug

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
