import math, random, sys, time
import pygame
from enum import Enum

# ---------------
# CONFIG / COLORS
# ---------------
WIDTH, HEIGHT = 1280, 720
FPS = 60
GRAVITY = 0.8
JUMP_VELOCITY = -15.0
DOUBLE_JUMP_VELOCITY = -13.5
MOVE_SPEED = 6.5
AIR_CONTROL = 0.7
FRICTION = 0.88
AIR_RESISTANCE = 0.96
TERMINAL_VELOCITY = 18.0

# Enhanced color palette
COLOR_BG_TOP = (20, 24, 40)
COLOR_BG_BOTTOM = (45, 35, 60)
COLOR_FG = (240, 240, 250)
COLOR_PLATFORM = (52, 62, 88)
COLOR_PLATFORM_EDGE = (72, 82, 108)
COLOR_SHADOW = (0, 0, 0, 100)
COLOR_SPIKE = (220, 60, 60)
COLOR_SPIKE_WARN = (255, 200, 80)
COLOR_WALL = (85, 105, 140)
COLOR_WALL_CRACK = (240, 245, 255)
COLOR_DOOR = (120, 200, 180)
COLOR_DOOR_LOCKED = (80, 120, 160)
COLOR_PLAYER = (240, 248, 255)
COLOR_PLAYER_SHADOW = (200, 208, 215)
COLOR_PARTICLE = (255, 255, 255)
COLOR_DUST = (180, 180, 200)
COLOR_IMPACT = (255, 180, 80)

# Game states
class GameState(Enum):
    PLAYING = 1
    DEAD = 2
    WON = 3
    PAUSED = 4

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Enhanced Devilish Platformer")
clock = pygame.time.Clock()

# Enhanced fonts
FONT_SMALL = pygame.font.SysFont("Segoe UI", 16)
FONT = pygame.font.SysFont("Segoe UI", 24, bold=True)
FONT_BIG = pygame.font.SysFont("Segoe UI", 36, bold=True)
FONT_HUGE = pygame.font.SysFont("Segoe UI", 48, bold=True)

# ---- Enhanced Helpers ----
def draw_vertical_gradient(surf, top_color, bottom_color, rect=None):
    if rect is None:
        rect = surf.get_rect()
    
    for y in range(rect.height):
        t = y / (rect.height - 1) if rect.height > 1 else 0
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surf, (r, g, b), (rect.x, rect.y + y), (rect.x + rect.width, rect.y + y))

def draw_enhanced_shadow(surf, rect, offset=(4, 4), blur=8, alpha=60):
    """Enhanced shadow with blur effect"""
    shadow_surf = pygame.Surface((rect.width + blur*2, rect.height + blur*2), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(blur, blur, rect.width, rect.height)
    
    # Create multiple shadow layers for blur effect
    for i in range(blur):
        alpha_val = alpha * (1 - i/blur) // 2
        expanded = shadow_rect.inflate(i*2, i*2)
        pygame.draw.rect(shadow_surf, (0, 0, 0, alpha_val), expanded, border_radius=8)
    
    surf.blit(shadow_surf, (rect.x + offset[0] - blur, rect.y + offset[1] - blur), 
              special_flags=pygame.BLEND_ALPHA_SDL2)

def draw_text(surf, text, pos, font, color=COLOR_FG, align='center', shadow=True):
    """Enhanced text rendering with shadow"""
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect()
    
    if align == 'center':
        text_rect.center = pos
    elif align == 'left':
        text_rect.midleft = pos
    elif align == 'right':
        text_rect.midright = pos
    
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0, 120))
        surf.blit(shadow_surf, (text_rect.x + 2, text_rect.y + 2))
    
    surf.blit(text_surf, text_rect)
    return text_rect

# ---- Particle System ----
class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def add_explosion(self, pos, count=20, color=COLOR_IMPACT, vel_range=(-5, 5)):
        for _ in range(count):
            vx = random.uniform(vel_range[0], vel_range[1])
            vy = random.uniform(vel_range[0], -1)
            life = random.uniform(0.5, 1.2)
            size = random.uniform(2, 5)
            self.particles.append({
                'pos': list(pos),
                'vel': [vx, vy],
                'life': life,
                'max_life': life,
                'color': color,
                'size': size
            })
    
    def add_dust(self, pos, count=5):
        for _ in range(count):
            vx = random.uniform(-1, 1)
            vy = random.uniform(-2, -0.5)
            life = random.uniform(0.3, 0.8)
            self.particles.append({
                'pos': list(pos),
                'vel': [vx, vy],
                'life': life,
                'max_life': life,
                'color': COLOR_DUST,
                'size': random.uniform(1, 3)
            })
    
    def update(self, dt):
        for particle in self.particles[:]:
            particle['vel'][1] += GRAVITY * 0.3
            particle['pos'][0] += particle['vel'][0]
            particle['pos'][1] += particle['vel'][1]
            particle['life'] -= dt
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
    
    def draw(self, surf):
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            color = (*particle['color'][:3], alpha)
            size = max(1, int(particle['size'] * (particle['life'] / particle['max_life'])))
            
            temp_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, color, (size, size), size)
            surf.blit(temp_surf, (particle['pos'][0] - size, particle['pos'][1] - size),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

# ---- Camera System ----
class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.target_x = 0
        self.target_y = 0
        self.shake_intensity = 0
        self.shake_duration = 0
    
    def follow(self, target_rect, smooth=0.1):
        self.target_x = target_rect.centerx - WIDTH // 2
        self.target_y = target_rect.centery - HEIGHT // 2
        
        # Smooth following
        self.x += (self.target_x - self.x) * smooth
        self.y += (self.target_y - self.y) * smooth
        
        # Keep camera in bounds
        self.x = max(0, min(self.x, WIDTH - WIDTH))  # Adjust based on level width
        self.y = max(-HEIGHT//4, min(self.y, HEIGHT//4))
    
    def add_shake(self, intensity, duration):
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)
    
    def update(self, dt):
        if self.shake_duration > 0:
            self.shake_duration -= dt
            if self.shake_duration <= 0:
                self.shake_intensity = 0
    
    def get_offset(self):
        offset_x = -self.x
        offset_y = -self.y
        
        if self.shake_intensity > 0:
            offset_x += random.uniform(-self.shake_intensity, self.shake_intensity)
            offset_y += random.uniform(-self.shake_intensity, self.shake_intensity)
        
        return int(offset_x), int(offset_y)

# ---- Enhanced Platform ----
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, platform_type='normal'):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.platform_type = platform_type
        self.create_surface()
    
    def create_surface(self):
        self.image = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Main platform
        pygame.draw.rect(self.image, COLOR_PLATFORM, (0, 0, self.rect.width, self.rect.height), 
                        border_radius=8)
        
        # Edge highlight
        pygame.draw.rect(self.image, COLOR_PLATFORM_EDGE, 
                        (0, 0, self.rect.width, 4), border_radius=8)
        
        # Add some texture
        for i in range(0, self.rect.width, 20):
            pygame.draw.line(self.image, COLOR_PLATFORM_EDGE, 
                           (i, self.rect.height-2), (i+8, self.rect.height-2))
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        draw_rect = pygame.Rect(*draw_pos, self.rect.width, self.rect.height)
        
        draw_enhanced_shadow(surf, draw_rect)
        surf.blit(self.image, draw_pos)

# ---- Enhanced Magic Wall ----
class MagicWall(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.alive = True
        self.cracked = False
        self.crack_timer = 0
        self.crack_progress = 0
        self.health = 2  # Requires 2 hits
        self.shake_timer = 0
        
    def hit(self):
        if not self.alive:
            return False
            
        self.health -= 1
        self.shake_timer = 0.3
        
        if self.health <= 0:
            self.alive = False
            return True  # Wall destroyed
        else:
            self.cracked = True
            self.crack_timer = 0.8
            return False  # Wall damaged
    
    def update(self, dt):
        if self.shake_timer > 0:
            self.shake_timer -= dt
        
        if self.cracked and self.crack_timer > 0:
            self.crack_timer -= dt
            self.crack_progress = 1 - (self.crack_timer / 0.8)
    
    def draw(self, surf, camera_offset):
        if not self.alive:
            return
            
        draw_pos = list(self.rect.topleft)
        draw_pos[0] += camera_offset[0]
        draw_pos[1] += camera_offset[1]
        
        # Add shake effect
        if self.shake_timer > 0:
            draw_pos[0] += random.uniform(-3, 3)
            draw_pos[1] += random.uniform(-1, 1)
        
        draw_rect = pygame.Rect(*draw_pos, self.rect.width, self.rect.height)
        draw_enhanced_shadow(surf, draw_rect)
        
        # Main wall
        pygame.draw.rect(surf, COLOR_WALL, draw_rect, border_radius=8)
        
        # Cracks
        if self.cracked:
            crack_alpha = int(255 * self.crack_progress)
            crack_color = (*COLOR_WALL_CRACK[:3], crack_alpha)
            
            # Draw crack lines
            center = draw_rect.center
            for i in range(6):
                angle = i * math.pi / 3 + self.crack_progress * 0.5
                length = self.rect.width * 0.4 * self.crack_progress
                end_x = center[0] + math.cos(angle) * length
                end_y = center[1] + math.sin(angle) * length
                
                temp_surf = pygame.Surface((abs(end_x - center[0]) + 4, abs(end_y - center[1]) + 4), pygame.SRCALPHA)
                pygame.draw.line(temp_surf, crack_color, 
                               (2, 2), (end_x - center[0] + 2, end_y - center[1] + 2), 3)
                surf.blit(temp_surf, (min(center[0], end_x) - 2, min(center[1], end_y) - 2),
                         special_flags=pygame.BLEND_ALPHA_SDL2)

# ---- Enhanced Spike ----
class Spike(pygame.sprite.Sprite):
    def __init__(self, x, y, w=32, h=26, popup=False, delay=0, move_pattern=None):
        super().__init__()
        self.base_rect = pygame.Rect(x, y, w, h)
        self.rect = self.base_rect.copy()
        self.popup = popup
        self.delay = delay
        self.timer = delay
        self.active = not popup
        self.warn_phase = 0
        self.move_pattern = move_pattern or {'type': 'none'}
        self.move_timer = 0
        self.original_pos = (x, y)
        
    def update(self, dt):
        if self.popup and not self.active:
            self.timer -= dt
            self.warn_phase += dt * 8
            if self.timer <= 0:
                self.active = True
        
        # Movement patterns
        self.move_timer += dt
        if self.move_pattern['type'] == 'horizontal':
            speed = self.move_pattern.get('speed', 2)
            range_val = self.move_pattern.get('range', 100)
            self.rect.x = self.original_pos[0] + math.sin(self.move_timer * speed) * range_val
        elif self.move_pattern['type'] == 'vertical':
            speed = self.move_pattern.get('speed', 1.5)
            range_val = self.move_pattern.get('range', 50)
            self.rect.y = self.original_pos[1] + math.sin(self.move_timer * speed) * range_val
    
    def get_danger_zone(self):
        """Returns the actual dangerous area (triangle shape)"""
        if not self.active:
            return None
        return [
            (self.rect.centerx, self.rect.top),
            (self.rect.left + 4, self.rect.bottom - 4),
            (self.rect.right - 4, self.rect.bottom - 4)
        ]
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        
        if self.popup and not self.active:
            # Warning effect
            intensity = math.sin(self.warn_phase) * 0.5 + 0.5
            warn_size = 4 + int(intensity * 8)
            warn_color = COLOR_SPIKE_WARN
            
            # Warning glow
            glow_surf = pygame.Surface((self.rect.width + warn_size*2, self.rect.height + warn_size*2), pygame.SRCALPHA)
            glow_center = (self.rect.width//2 + warn_size, warn_size)
            pygame.draw.circle(glow_surf, (*warn_color, int(100 * intensity)), glow_center, warn_size*2)
            surf.blit(glow_surf, (draw_pos[0] - warn_size, draw_pos[1] - warn_size), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        if self.active:
            # Main spike triangle
            points = [
                (draw_pos[0] + self.rect.width//2, draw_pos[1]),
                (draw_pos[0] + 4, draw_pos[1] + self.rect.height),
                (draw_pos[0] + self.rect.width - 4, draw_pos[1] + self.rect.height)
            ]
            
            # Shadow
            shadow_points = [(p[0] + 2, p[1] + 2) for p in points]
            pygame.draw.polygon(surf, (0, 0, 0, 100), shadow_points)
            
            # Main spike
            pygame.draw.polygon(surf, COLOR_SPIKE, points)
            # Highlight edge
            pygame.draw.polygon(surf, (255, 100, 100), points, 2)

# ---- Enhanced Falling Stone ----
class FallingStone(pygame.sprite.Sprite):
    def __init__(self, x, top_y, trigger_range, warning_time=1.0):
        super().__init__()
        self.rect = pygame.Rect(x, top_y, 45, 45)
        self.vy = 0
        self.vx = 0
        self.rotation = 0
        self.angular_velocity = 0
        self.dropped = False
        self.settled = False
        self.warning = False
        self.warning_timer = warning_time
        self.trigger_range = trigger_range
        self.bounces = 0
        self.max_bounces = 2
    
    def trigger_check(self, player_x):
        if not self.dropped and not self.warning:
            if self.trigger_range[0] <= player_x <= self.trigger_range[1]:
                self.warning = True
    
    def update(self, dt, platforms, particles):
        if self.warning and not self.dropped:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.dropped = True
                self.vy = 0
                self.angular_velocity = random.uniform(-5, 5)
        
        if self.dropped and not self.settled:
            # Realistic physics
            self.vy += GRAVITY * 1.5
            self.vy = min(self.vy, TERMINAL_VELOCITY)
            
            old_pos = self.rect.copy()
            self.rect.x += int(self.vx)
            self.rect.y += int(self.vy)
            self.rotation += self.angular_velocity * dt
            
            # Collision with platforms
            for platform in platforms:
                if self.rect.colliderect(platform.rect):
                    if self.bounces < self.max_bounces:
                        # Bounce
                        self.rect.bottom = platform.rect.top
                        self.vy = -self.vy * 0.4  # Energy loss
                        self.vx += random.uniform(-2, 2)  # Random horizontal component
                        self.angular_velocity *= 0.7
                        self.bounces += 1
                        
                        # Impact particles
                        particles.add_explosion(
                            (self.rect.centerx, self.rect.bottom),
                            count=15,
                            color=COLOR_IMPACT
                        )
                    else:
                        # Settle
                        self.rect.bottom = platform.rect.top
                        self.vy = 0
                        self.vx *= 0.8  # Friction
                        self.angular_velocity *= 0.9
                        if abs(self.vx) < 0.1 and abs(self.angular_velocity) < 0.1:
                            self.settled = True
                        
                        # Final impact particles
                        particles.add_explosion(
                            (self.rect.centerx, self.rect.bottom),
                            count=25,
                            color=COLOR_IMPACT
                        )
                    break
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        
        if self.warning and not self.dropped:
            # Warning indicator
            alpha = int(128 + 127 * math.sin(self.warning_timer * 10))
            warning_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
            pygame.draw.rect(warning_surf, (255, 200, 0, alpha), 
                           (10, 10, self.rect.width, self.rect.height), border_radius=8)
            surf.blit(warning_surf, (draw_pos[0] - 10, draw_pos[1] - 10), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Create rotated stone surface
        stone_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Shadow
        shadow_rect = pygame.Rect(2, 2, self.rect.width-2, self.rect.height-2)
        pygame.draw.rect(stone_surf, (0, 0, 0, 100), shadow_rect, border_radius=8)
        
        # Main stone
        main_rect = pygame.Rect(0, 0, self.rect.width, self.rect.height)
        pygame.draw.rect(stone_surf, (140, 140, 160), main_rect, border_radius=8)
        pygame.draw.rect(stone_surf, (160, 160, 180), main_rect, width=3, border_radius=8)
        
        # Add stone texture
        for i in range(3):
            for j in range(3):
                x = i * self.rect.width // 3 + random.randint(-2, 2)
                y = j * self.rect.height // 3 + random.randint(-2, 2)
                pygame.draw.circle(stone_surf, (120, 120, 140), (x, y), 2)
        
        # Rotate the surface
        if abs(self.rotation) > 0.1:
            rotated_surf = pygame.transform.rotate(stone_surf, math.degrees(self.rotation))
            rotated_rect = rotated_surf.get_rect(center=(draw_pos[0] + self.rect.width//2, 
                                                        draw_pos[1] + self.rect.height//2))
            surf.blit(rotated_surf, rotated_rect)
        else:
            surf.blit(stone_surf, draw_pos)

# ---- Enhanced Door ----
class Door:
    def __init__(self, pos1, pos2):
        self.rect = pygame.Rect(pos1[0], pos1[1], 40, 60)
        self.alt_pos = pos2
        self.trolled_once = False
        self.open = False
        self.pulse = 0
        self.glow_intensity = 0
        self.teleport_particles = []
        
    def maybe_troll(self, player_rect, particles):
        # Only troll if player approaches from the sides or top, not from bottom
        if (not self.trolled_once and 
            player_rect.colliderect(self.rect.inflate(60, 20)) and
            player_rect.centery <= self.rect.centery):  # Not from bottom
            
            old_pos = self.rect.center
            self.rect.topleft = self.alt_pos
            self.trolled_once = True
            
            # Add teleport particles at both locations
            particles.add_explosion(old_pos, count=30, color=COLOR_DOOR)
            particles.add_explosion(self.rect.center, count=30, color=COLOR_DOOR)
    
    def set_open(self):
        self.open = True
        self.glow_intensity = 1.0
    
    def update(self, dt):
        self.pulse += dt * 3
        if self.open and self.glow_intensity > 0:
            self.glow_intensity = min(1.0, self.glow_intensity + dt * 2)
    
    def check_win_collision(self, player_rect):
        """Only allow winning if player approaches from sides/top, not bottom"""
        if (self.open and 
            player_rect.colliderect(self.rect.inflate(-5, -5)) and
            player_rect.centery <= self.rect.centery + 10):  # Small tolerance for bottom
            return True
        return False
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        draw_rect = pygame.Rect(*draw_pos, self.rect.width, self.rect.height)
        
        # Glow effect
        if self.open:
            glow_radius = int(30 + 15 * math.sin(self.pulse))
            glow_color = (*COLOR_DOOR, int(60 * self.glow_intensity))
            glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
            surf.blit(glow_surf, (draw_rect.centerx - glow_radius, draw_rect.centery - glow_radius), 
                     special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Door shadow
        draw_enhanced_shadow(surf, draw_rect)
        
        # Door frame
        door_color = COLOR_DOOR if self.open else COLOR_DOOR_LOCKED
        pygame.draw.rect(surf, door_color, draw_rect, border_radius=8)
        
        # Door interior
        inner_rect = draw_rect.inflate(-12, -16)
        if self.open:
            # Swirling portal effect
            portal_color = (100, 255, 200, 150)
            for i in range(3):
                angle = self.pulse + i * (2 * math.pi / 3)
                radius = inner_rect.width // 4
                center_x = inner_rect.centerx + math.cos(angle) * radius // 3
                center_y = inner_rect.centery + math.sin(angle) * radius // 3
                pygame.draw.circle(surf, portal_color, (int(center_x), int(center_y)), radius//2)
        else:
            pygame.draw.rect(surf, (30, 30, 40), inner_rect, border_radius=4)
        
        # Door handle
        handle_pos = (draw_rect.right - 12, draw_rect.centery)
        pygame.draw.circle(surf, (200, 200, 210), handle_pos, 4)

# ---- Enhanced Player ----
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 32, 44)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.can_double_jump = False
        self.has_double_jumped = False
        self.dead = False
        self.win = False
        self.facing_right = True
        self.animation_timer = 0
        self.squash_stretch = 1.0  # For impact animation
        self.coyote_time = 0.1  # Grace period for jumping after leaving ground
        self.coyote_timer = 0
        self.jump_buffer_time = 0.1  # Buffer for early jump input
        self.jump_buffer_timer = 0
        self.wall_slide_timer = 0
        self.dust_timer = 0
    
    def control(self, keys, dt):
        # Horizontal movement
        move_input = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_input -= 1
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_input += 1
            self.facing_right = True
        
        # Enhanced movement with air control
        control_strength = 1.0 if self.on_ground else AIR_CONTROL
        target_vx = move_input * MOVE_SPEED
        accel = 0.8 if self.on_ground else 0.4
        
        self.vx = self.vx + (target_vx - self.vx) * accel * control_strength
        
        # Apply friction/air resistance
        if self.on_ground:
            if abs(move_input) < 0.1:  # Not actively moving
                self.vx *= FRICTION
        else:
            self.vx *= AIR_RESISTANCE
        
        # Jump input buffering
        jump_pressed = keys[pygame.K_w] or keys[pygame.K_SPACE] or keys[pygame.K_UP]
        if jump_pressed:
            self.jump_buffer_timer = self.jump_buffer_time
        
        # Handle jumping
        if self.jump_buffer_timer > 0:
            if self.coyote_timer > 0:  # Regular jump
                self.vy = JUMP_VELOCITY
                self.on_ground = False
                self.can_double_jump = True
                self.coyote_timer = 0
                self.jump_buffer_timer = 0
            elif self.can_double_jump and not self.has_double_jumped:  # Double jump
                self.vy = DOUBLE_JUMP_VELOCITY
                self.has_double_jumped = True
                self.can_double_jump = False
                self.jump_buffer_timer = 0
        
        # Update timers
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt
        if self.coyote_timer > 0:
            self.coyote_timer -= dt
    
    def physics(self, dt, platforms, particles):
        # Apply gravity
        if not self.on_ground:
            self.vy += GRAVITY
            self.vy = min(self.vy, TERMINAL_VELOCITY)
        
        # Store old position for collision resolution
        old_rect = self.rect.copy()
        
        # Horizontal movement
        self.rect.x += int(self.vx)
        
        # Horizontal collisions
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:  # Moving right
                    self.rect.right = platform.rect.left
                    self.vx = 0
                elif self.vx < 0:  # Moving left
                    self.rect.left = platform.rect.right
                    self.vx = 0
        
        # Vertical movement
        self.rect.y += int(self.vy)
        
        # Vertical collisions
        was_on_ground = self.on_ground
        self.on_ground = False
        
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:  # Falling down
                    self.rect.bottom = platform.rect.top
                    if self.vy > 8:  # Hard landing
                        self.squash_stretch = 0.7
                        particles.add_dust((self.rect.centerx, self.rect.bottom), count=8)
                    self.vy = 0
                    self.on_ground = True
                    self.has_double_jumped = False
                    self.can_double_jump = True
                elif self.vy < 0:  # Jumping up
                    self.rect.top = platform.rect.bottom
                    self.vy = 0
        
        # Coyote time - grace period for jumping after leaving ground
        if was_on_ground and not self.on_ground:
            self.coyote_timer = self.coyote_time
        elif self.on_ground:
            self.coyote_timer = self.coyote_time
        
        # Keep player in bounds
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)
        
        if self.rect.top < 0:
            self.rect.top = 0
            self.vy = max(0, self.vy)
        
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT
            self.vy = 0
            self.on_ground = True
        
        # Generate dust particles when moving on ground
        if self.on_ground and abs(self.vx) > 2:
            self.dust_timer += dt
            if self.dust_timer > 0.1:
                particles.add_dust((self.rect.centerx + random.randint(-8, 8), self.rect.bottom))
                self.dust_timer = 0
        
        # Update animation
        self.animation_timer += dt
        
        # Squash/stretch recovery
        if self.squash_stretch < 1.0:
            self.squash_stretch = min(1.0, self.squash_stretch + dt * 4)
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        
        # Calculate squashed dimensions
        draw_width = int(self.rect.width * (2 - self.squash_stretch))
        draw_height = int(self.rect.height * self.squash_stretch)
        
        draw_rect = pygame.Rect(
            draw_pos[0] - (draw_width - self.rect.width) // 2,
            draw_pos[1] + (self.rect.height - draw_height),
            draw_width,
            draw_height
        )
        
        # Shadow
        draw_enhanced_shadow(surf, draw_rect, offset=(3, 3))
        
        # Main body
        pygame.draw.rect(surf, COLOR_PLAYER, draw_rect, border_radius=8)
        
        # Body highlight
        highlight_rect = draw_rect.inflate(-4, -4)
        highlight_rect.height = max(4, highlight_rect.height // 3)
        pygame.draw.rect(surf, COLOR_PLAYER_SHADOW, highlight_rect, border_radius=6)
        
        # Eyes
        eye_y = draw_rect.y + max(8, draw_height // 4)
        eye_offset = 6 if draw_width > 24 else 4
        
        # Eye direction based on movement
        eye_dir = 0
        if abs(self.vx) > 0.5:
            eye_dir = 1 if self.vx > 0 else -1
        
        left_eye_x = draw_rect.centerx - eye_offset + eye_dir
        right_eye_x = draw_rect.centerx + eye_offset + eye_dir
        
        pygame.draw.circle(surf, (40, 40, 60), (left_eye_x, eye_y), 3)
        pygame.draw.circle(surf, (40, 40, 60), (right_eye_x, eye_y), 3)
        
        # Eye shine
        pygame.draw.circle(surf, COLOR_FG, (left_eye_x - 1, eye_y - 1), 1)
        pygame.draw.circle(surf, COLOR_FG, (right_eye_x - 1, eye_y - 1), 1)
        
        # Mouth (changes based on state)
        mouth_y = draw_rect.y + max(20, draw_height * 2 // 3)
        if not self.on_ground and self.vy > 5:  # Falling
            # Surprised expression
            pygame.draw.ellipse(surf, (40, 40, 60), 
                              (draw_rect.centerx - 4, mouth_y - 2, 8, 6))
        else:
            # Happy expression
            mouth_points = [
                (draw_rect.centerx - 6, mouth_y),
                (draw_rect.centerx, mouth_y + 3),
                (draw_rect.centerx + 6, mouth_y)
            ]
            pygame.draw.lines(surf, (40, 40, 60), False, mouth_points, 2)
        
        # Movement lines for speed effect
        if abs(self.vx) > 4:
            for i in range(3):
                line_x = draw_rect.left - 8 - i*4 if self.vx > 0 else draw_rect.right + 8 + i*4
                line_alpha = 100 - i * 30
                line_surf = pygame.Surface((6, 2), pygame.SRCALPHA)
                pygame.draw.rect(line_surf, (255, 255, 255, line_alpha), (0, 0, 6, 2))
                surf.blit(line_surf, (line_x, draw_rect.centery + i*3 - 3), special_flags=pygame.BLEND_ALPHA_SDL2)

# ---- Game Class ----
class Game:
    def __init__(self):
        self.state = GameState.PLAYING
        self.camera = Camera()
        self.particles = ParticleSystem()
        self.start_time = time.time()
        self.death_time = None
        self.win_time = None
        self.best_time = float('inf')
        self.attempts = 0
        
        self.setup_level()
    
    def setup_level(self):
        """Create the enhanced level with realistic physics"""
        self.platforms = []
        
        # Ground and main platforms
        self.platforms.append(Platform(0, HEIGHT-50, WIDTH, 50))  # Ground
        self.platforms.append(Platform(120, HEIGHT-160, 200, 20))  # First ledge
        self.platforms.append(Platform(400, HEIGHT-240, 160, 20))  # Mid platform
        self.platforms.append(Platform(640, HEIGHT-320, 180, 20))  # High platform
        self.platforms.append(Platform(900, HEIGHT-200, 200, 20))  # Right platform
        self.platforms.append(Platform(1100, HEIGHT-280, 120, 20)) # Final approach
        
        # Additional challenge platforms
        self.platforms.append(Platform(300, HEIGHT-120, 80, 16))   # Small step
        self.platforms.append(Platform(580, HEIGHT-160, 60, 16))   # Gap bridge
        self.platforms.append(Platform(820, HEIGHT-240, 70, 16))   # Precision jump
        
        # Magic wall - now requires multiple hits
        self.magic_wall = MagicWall(350, HEIGHT-140, 70, 80)
        
        # Enhanced spikes with different patterns
        self.spikes = [
            Spike(180, HEIGHT-178, w=32, h=26, popup=False),  # Static warning
            Spike(450, HEIGHT-258, w=32, h=26, popup=True, delay=2.0),  # Delayed popup
            Spike(700, HEIGHT-338, w=32, h=26, popup=False, 
                  move_pattern={'type': 'horizontal', 'speed': 2, 'range': 60}),  # Moving
            Spike(950, HEIGHT-218, w=32, h=26, popup=True, delay=1.0),  # Another popup
            Spike(1150, HEIGHT-298, w=32, h=26, popup=False,
                  move_pattern={'type': 'vertical', 'speed': 1.5, 'range': 30}),  # Vertical movement
        ]
        
        # Multiple falling stones with different triggers
        self.falling_stones = [
            FallingStone(480, 50, trigger_range=(420, 540), warning_time=1.5),
            FallingStone(680, 30, trigger_range=(600, 720), warning_time=1.0),
            FallingStone(980, 40, trigger_range=(920, 1020), warning_time=2.0),
        ]
        
        # Enhanced door with proper collision
        self.door = Door(pos1=(1140, HEIGHT-340), pos2=(160, HEIGHT-220))
        
        # Win trigger - must reach the end area
        self.win_trigger = pygame.Rect(WIDTH-60, 0, 60, HEIGHT)
        
        # Player
        self.player = Player(60, HEIGHT-100)
    
    def handle_collisions(self):
        """Enhanced collision detection"""
        if self.state != GameState.PLAYING:
            return
        
        # Wall collision - now requires multiple hits
        if (self.magic_wall.alive and 
            self.player.rect.colliderect(self.magic_wall.rect.inflate(5, 5))):
            
            if self.magic_wall.hit():  # Wall destroyed
                self.particles.add_explosion(
                    self.magic_wall.rect.center, 
                    count=50, 
                    color=COLOR_WALL_CRACK
                )
                self.camera.add_shake(8, 0.5)
            else:  # Wall damaged
                self.particles.add_explosion(
                    (self.player.rect.centerx, self.magic_wall.rect.centery),
                    count=20,
                    color=COLOR_WALL_CRACK
                )
                self.camera.add_shake(4, 0.3)
        
        # Spike collisions - use precise triangle collision
        for spike in self.spikes:
            danger_zone = spike.get_danger_zone()
            if danger_zone and self.point_in_triangle_collision(self.player.rect, danger_zone):
                self.kill_player()
                return
        
        # Falling stone collisions
        for stone in self.falling_stones:
            if stone.rect.colliderect(self.player.rect):
                self.kill_player()
                return
        
        # Door interactions
        self.door.maybe_troll(self.player.rect, self.particles)
        
        # Win condition - check if door is open and proper collision
        if self.player.rect.colliderect(self.win_trigger):
            self.door.set_open()
        
        if self.door.check_win_collision(self.player.rect):
            self.win_game()
    
    def point_in_triangle_collision(self, rect, triangle_points):
        """Check if rectangle overlaps with triangle"""
        # Simple overlap check - test if any corner of rect is inside triangle
        corners = [
            (rect.left, rect.top), (rect.right, rect.top),
            (rect.left, rect.bottom), (rect.right, rect.bottom),
            (rect.centerx, rect.centery)  # Also check center
        ]
        
        for corner in corners:
            if self.point_in_triangle(corner, triangle_points):
                return True
        return False
    
    def point_in_triangle(self, point, triangle):
        """Check if point is inside triangle using barycentric coordinates"""
        x, y = point
        x1, y1 = triangle[0]
        x2, y2 = triangle[1]
        x3, y3 = triangle[2]
        
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(denominator) < 0.001:
            return False
        
        a = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / denominator
        b = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / denominator
        c = 1 - a - b
        
        return a >= 0 and b >= 0 and c >= 0
    
    def kill_player(self):
        self.state = GameState.DEAD
        self.player.dead = True
        self.death_time = time.time()
        self.attempts += 1
        
        # Death particles
        self.particles.add_explosion(
            self.player.rect.center,
            count=40,
            color=(255, 100, 100),
            vel_range=(-8, 8)
        )
        self.camera.add_shake(12, 0.8)
    
    def win_game(self):
        self.state = GameState.WON
        self.player.win = True
        self.win_time = time.time()
        
        current_time = self.win_time - self.start_time
        if current_time < self.best_time:
            self.best_time = current_time
        
        # Victory particles
        self.particles.add_explosion(
            self.player.rect.center,
            count=60,
            color=COLOR_DOOR,
            vel_range=(-6, 6)
        )
        self.camera.add_shake(6, 0.5)
    
    def reset_game(self):
        self.state = GameState.PLAYING
        self.start_time = time.time()
        self.death_time = None
        self.win_time = None
        self.setup_level()
        self.particles = ParticleSystem()
        self.camera = Camera()
    
    def update(self, dt, keys):
        # Handle input
        if keys[pygame.K_r]:
            self.reset_game()
            return True  # Continue game after reset
        
        if keys[pygame.K_ESCAPE]:
            return False  # Quit game
        
        # Update game objects
        if self.state == GameState.PLAYING:
            self.player.control(keys, dt)
        
        # Physics for all objects
        platforms_for_collision = [p for p in self.platforms]
        if self.magic_wall.alive:
            platforms_for_collision.append(Platform(self.magic_wall.rect.x, self.magic_wall.rect.y,
                                                   self.magic_wall.rect.width, self.magic_wall.rect.height))
        
        self.player.physics(dt, platforms_for_collision, self.particles)
        
        # Update other objects
        for spike in self.spikes:
            spike.update(dt)
        
        for stone in self.falling_stones:
            stone.trigger_check(self.player.rect.centerx)
            stone.update(dt, self.platforms, self.particles)
        
        self.magic_wall.update(dt)
        self.door.update(dt)
        
        # Update systems
        self.particles.update(dt)
        self.camera.follow(self.player.rect, smooth=0.12)
        self.camera.update(dt)
        
        # Collision detection
        self.handle_collisions()
        
        return True
    
    def draw(self, surf):
        # Clear screen
        surf.fill((0, 0, 0))
        
        # Background gradient
        draw_vertical_gradient(surf, COLOR_BG_TOP, COLOR_BG_BOTTOM)
        
        # Atmospheric effects
        self.draw_atmosphere(surf)
        
        # Get camera offset
        camera_offset = self.camera.get_offset()
        
        # Draw game objects
        for platform in self.platforms:
            platform.draw(surf, camera_offset)
        
        self.magic_wall.draw(surf, camera_offset)
        
        for spike in self.spikes:
            spike.draw(surf, camera_offset)
        
        for stone in self.falling_stones:
            stone.draw(surf, camera_offset)
        
        self.door.draw(surf, camera_offset)
        self.player.draw(surf, camera_offset)
        
        # Draw particles
        self.particles.draw(surf)
        
        # UI
        self.draw_ui(surf)
    
    def draw_atmosphere(self, surf):
        """Draw atmospheric effects"""
        t = pygame.time.get_ticks() / 1000.0
        
        # Floating fog layers
        for i in range(4):
            y = int(100 + i * 120 + math.sin(t * 0.3 + i) * 20)
            alpha = 30 + int(20 * math.sin(t * 0.5 + i))
            
            fog_surf = pygame.Surface((WIDTH + 200, 80), pygame.SRCALPHA)
            pygame.draw.ellipse(fog_surf, (255, 255, 255, alpha), (0, 0, WIDTH + 200, 80))
            surf.blit(fog_surf, (-100 + i * 30, y), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Parallax background elements
        for i in range(6):
            star_x = int((i * 200 + math.sin(t * 0.1 + i) * 30) % WIDTH)
            star_y = int(50 + i * 60)
            brightness = int(100 + 50 * math.sin(t + i))
            pygame.draw.circle(surf, (brightness, brightness, brightness), 
                             (star_x, star_y), 2)
    
    def draw_ui(self, surf):
        """Enhanced UI with better information display"""
        # Game title
        title_color = COLOR_FG
        if self.state == GameState.DEAD:
            title_color = (255, 100, 100)
        elif self.state == GameState.WON:
            title_color = (100, 255, 150)
        
        title_text = "ENHANCED DEVILISH PLATFORMER"
        if self.state == GameState.DEAD:
            title_text = "💀 YOU DIED 💀"
        elif self.state == GameState.WON:
            title_text = "🎉 VICTORY! 🎉"
        
        draw_text(surf, title_text, (WIDTH // 2, 40), FONT_BIG, title_color)
        
        # Timer
        current_time = time.time() - self.start_time
        if self.state == GameState.DEAD and self.death_time:
            current_time = self.death_time - self.start_time
        elif self.state == GameState.WON and self.win_time:
            current_time = self.win_time - self.start_time
        
        timer_text = f"Time: {current_time:.2f}s"
        draw_text(surf, timer_text, (WIDTH - 100, 30), FONT, align='right')
        
        # Attempts counter
        attempts_text = f"Attempts: {self.attempts}"
        draw_text(surf, attempts_text, (WIDTH - 100, 60), FONT, align='right')
        
        # Best time
        if self.best_time < float('inf'):
            best_text = f"Best: {self.best_time:.2f}s"
            draw_text(surf, best_text, (WIDTH - 100, 90), FONT, align='right')
        
        # Controls
        controls = [
            "Move: A/D or ←/→",
            "Jump: W/↑/Space (Double Jump Available!)",
            "Reset: R  |  Quit: ESC"
        ]
        
        for i, control in enumerate(controls):
            draw_text(surf, control, (WIDTH // 2, HEIGHT - 100 + i * 25), FONT_SMALL)
        
        # Game state messages
        if self.state == GameState.DEAD:
            draw_text(surf, "Press R to try again", (WIDTH // 2, HEIGHT // 2), FONT_BIG, (255, 200, 200))
        elif self.state == GameState.WON:
            draw_text(surf, "Incredible! Press R to play again", (WIDTH // 2, HEIGHT // 2), FONT_BIG, (200, 255, 200))
        elif self.state == GameState.PLAYING:
            # Gameplay tips
            tips = []
            if not self.door.trolled_once:
                tips.append("That door looks suspicious... 🤔")
            if self.magic_wall.alive:
                if self.magic_wall.cracked:
                    tips.append("The wall is cracking! Hit it again! 💥")
                else:
                    tips.append("Try breaking through that wall... 🧱")
            if not any(stone.warning or stone.dropped for stone in self.falling_stones):
                tips.append("Watch out for falling objects! ⚠")
            
            for i, tip in enumerate(tips[:2]):  # Show max 2 tips
                draw_text(surf, tip, (WIDTH // 2, 100 + i * 30), FONT_SMALL, (200, 200, 255))
        
        # Player info (debug-style info)
        if self.state == GameState.PLAYING:
            player_info = [
                f"Pos: ({self.player.rect.x}, {self.player.rect.y})",
                f"Vel: ({self.player.vx:.1f}, {self.player.vy:.1f})",
                f"Ground: {'Yes' if self.player.on_ground else 'No'}",
                f"Double Jump: {'Available' if self.player.can_double_jump else 'Used' if self.player.has_double_jumped else 'Ready'}"
            ]
            
            for i, info in enumerate(player_info):
                draw_text(surf, info, (100, HEIGHT - 120 + i * 20), FONT_SMALL, 
                         (150, 150, 150), align='left', shadow=False)

# ---- Main Game Loop ----
def main():
    game = Game()
    running = True
    
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Get keys
        keys = pygame.key.get_pressed()
        
        # Update game
        if not game.update(dt, keys):
            running = False
        
        # Draw everything
        game.draw(screen)
        pygame.display.flip()
    
    pygame.quit()
    return 0

if __name__== "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        pass