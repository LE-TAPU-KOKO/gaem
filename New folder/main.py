import math, random, sys, time
import pygame
import asyncio
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

def draw_enhanced_shadow(surf, rect, offset=(4, 4), blur=4, alpha=60):
    """Optimized shadow with reduced blur effect"""
    # Skip shadow rendering for small objects to improve performance
    if rect.width < 20 or rect.height < 20:
        return
        
    # Use a smaller blur radius
    shadow_surf = pygame.Surface((rect.width + blur*2, rect.height + blur*2), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(blur, blur, rect.width, rect.height)
    
    # Create fewer shadow layers (only 2 instead of blur count)
    for i in range(2):
        alpha_val = alpha * (1 - i/2) // 2
        expanded = shadow_rect.inflate(i*blur, i*blur)
        pygame.draw.rect(shadow_surf, (0, 0, 0, alpha_val), expanded, border_radius=4)
    
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

# ---- Optimized Particle System ----
class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.max_particles = 100  # Limit total particles
    
    def add_explosion(self, pos, count=10, color=COLOR_IMPACT, vel_range=(-5, 5)):
        # Reduce particle count for explosions
        count = min(count, 10)
        
        # Check if adding would exceed max particles
        if len(self.particles) + count > self.max_particles:
            # Remove oldest particles to make room
            self.particles = self.particles[-(self.max_particles - count):]
            
        for _ in range(count):
            vx = random.uniform(vel_range[0], vel_range[1])
            vy = random.uniform(vel_range[0], -1)
            life = random.uniform(0.5, 1.0)  # Slightly shorter life
            size = random.uniform(2, 4)  # Slightly smaller
            self.particles.append({
                'pos': list(pos),
                'vel': [vx, vy],
                'life': life,
                'max_life': life,
                'color': color,
                'size': size
            })
    
    def add_dust(self, pos, count=3):  # Reduced dust count
        # Check if adding would exceed max particles
        if len(self.particles) + count > self.max_particles:
            return  # Skip dust if too many particles
            
        for _ in range(count):
            vx = random.uniform(-1, 1)
            vy = random.uniform(-2, -0.5)
            life = random.uniform(0.2, 0.6)  # Shorter life
            self.particles.append({
                'pos': list(pos),
                'vel': [vx, vy],
                'life': life,
                'max_life': life,
                'color': COLOR_DUST,
                'size': random.uniform(1, 2)  # Smaller dust
            })
    
    def update(self, dt):
        # Use direct list comprehension instead of slice copy and remove
        self.particles = [p for p in self.particles if self._update_particle(p, dt)]
    
    def _update_particle(self, particle, dt):
        # Update single particle and return False if it should be removed
        particle['vel'][1] += GRAVITY * 0.3
        particle['pos'][0] += particle['vel'][0]
        particle['pos'][1] += particle['vel'][1]
        particle['life'] -= dt
        return particle['life'] > 0
    
    def draw(self, surf):
        # Use a single surface for all particles of the same size
        size_groups = {}
        
        for particle in self.particles:
            size = max(1, int(particle['size'] * (particle['life'] / particle['max_life'])))
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(particle)
        
        # Draw particles by size group
        for size, particles in size_groups.items():
            temp_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            
            for particle in particles:
                alpha = int(255 * (particle['life'] / particle['max_life']))
                color = (*particle['color'][:3], alpha)
                pygame.draw.circle(temp_surf, color, (size, size), size)
                surf.blit(temp_surf, (particle['pos'][0] - size, particle['pos'][1] - size),
                         special_flags=pygame.BLEND_ALPHA_SDL2)
                # Reset surface for next particle
                temp_surf.fill((0,0,0,0))

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

# ---- Fake Platform (Disappears when touched) ----
class FakePlatform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, delay=0.5):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.active = True
        self.triggered = False
        self.disappear_timer = 0
        self.disappear_delay = delay
        self.alpha = 255
        self.create_surface()
    
    def create_surface(self):
        self.image = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Slightly different color from normal platforms to hint it's special
        pygame.draw.rect(self.image, (180, 160, 140), (0, 0, self.rect.width, self.rect.height), 
                        border_radius=8)
        
        # Edge highlight
        pygame.draw.rect(self.image, (200, 180, 160), 
                        (0, 0, self.rect.width, 4), border_radius=8)
        
        # Add some texture
        for i in range(0, self.rect.width, 15):
            pygame.draw.line(self.image, (160, 140, 120), 
                           (i, self.rect.height-2), (i+6, self.rect.height-2))
    
    def trigger(self):
        if self.active and not self.triggered:
            self.triggered = True
            self.disappear_timer = self.disappear_delay
    
    def update(self, dt):
        if self.triggered:
            self.disappear_timer -= dt
            if self.disappear_timer <= 0:
                self.active = False
            else:
                # Fade out effect
                self.alpha = int(255 * (self.disappear_timer / self.disappear_delay))
    
    def draw(self, surf, camera_offset):
        if not self.active:
            return
            
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        
        if self.triggered:
            # Create a copy with alpha for fading effect
            faded_image = self.image.copy()
            faded_image.set_alpha(self.alpha)
            surf.blit(faded_image, draw_pos)
        else:
            draw_enhanced_shadow(surf, pygame.Rect(*draw_pos, self.rect.width, self.rect.height))
            surf.blit(self.image, draw_pos)

# ---- Teleport Trap ----
class TeleportTrap(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, dest):
        super().__init__()
        self.rect = pygame.Rect(x, y, w, h)
        self.destination = dest
        self.cooldown = 0
        self.cooldown_max = 3.0  # Seconds before it can teleport again
        self.pulse = 0
    
    def update(self, dt):
        if self.cooldown > 0:
            self.cooldown -= dt
        self.pulse = (self.pulse + dt * 5) % (2 * math.pi)
    
    def check_teleport(self, player_rect, particles):
        if self.cooldown <= 0 and player_rect.colliderect(self.rect):
            # Teleport effect
            particles.add_explosion(
                player_rect.center,
                count=40,
                color=(100, 200, 255),
                vel_range=(-6, 6)
            )
            
            # Set cooldown
            self.cooldown = self.cooldown_max
            
            # Return new position
            return self.destination
        return None
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        draw_rect = pygame.Rect(*draw_pos, self.rect.width, self.rect.height)
        
        # Glow effect
        glow_intensity = 0.5 + 0.5 * math.sin(self.pulse)
        glow_color = (100, 200, 255, int(100 * glow_intensity))
        glow_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, glow_color, (0, 0, self.rect.width + 20, self.rect.height + 20))
        surf.blit(glow_surf, (draw_pos[0] - 10, draw_pos[1] - 10), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Main trap
        color = (80, 180, 240) if self.cooldown <= 0 else (60, 120, 180)
        pygame.draw.rect(surf, color, draw_rect, border_radius=4)
        
        # Teleport symbol
        symbol_color = (220, 240, 255)
        center_x, center_y = draw_rect.centerx, draw_rect.centery
        pygame.draw.circle(surf, symbol_color, (center_x, center_y), min(self.rect.width, self.rect.height) // 4, 1)
        pygame.draw.line(surf, symbol_color, (center_x - 5, center_y - 5), (center_x + 5, center_y + 5), 1)
        pygame.draw.line(surf, symbol_color, (center_x + 5, center_y - 5), (center_x - 5, center_y + 5), 1)

# ---- Fake Door (Kills Player) ----
class FakeDoor(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 40, 60)
        self.pulse = 0
        self.triggered = False
        self.trigger_timer = 0
    
    def update(self, dt):
        self.pulse += dt * 2
        if self.triggered:
            self.trigger_timer -= dt
    
    def check_collision(self, player_rect):
        return player_rect.colliderect(self.rect.inflate(-10, -10))
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        draw_rect = pygame.Rect(*draw_pos, self.rect.width, self.rect.height)
        
        # Door shadow
        draw_enhanced_shadow(surf, draw_rect)
        
        # Door frame - slightly different color from real door
        door_color = (180, 120, 200)
        pygame.draw.rect(surf, door_color, draw_rect, border_radius=8)
        
        # Door interior
        inner_rect = draw_rect.inflate(-12, -16)
        pygame.draw.rect(surf, (40, 30, 50), inner_rect, border_radius=4)
        
        # Door handle
        handle_pos = (draw_rect.right - 12, draw_rect.centery)
        pygame.draw.circle(surf, (220, 180, 230), handle_pos, 4)
        
        # Subtle hint that it's fake (small skull symbol)
        if math.sin(self.pulse) > 0.8:
            skull_color = (200, 200, 200, 100)
            skull_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(skull_surf, skull_color, (5, 5), 3)
            pygame.draw.circle(skull_surf, skull_color, (3, 4), 1)
            pygame.draw.circle(skull_surf, skull_color, (7, 4), 1)
            pygame.draw.line(skull_surf, skull_color, (3, 7), (7, 7), 1)
            surf.blit(skull_surf, (draw_rect.centerx - 5, draw_rect.centery - 5), special_flags=pygame.BLEND_ALPHA_SDL2)

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
        try:
            if self.warning and not self.dropped:
                self.warning_timer -= dt
                if self.warning_timer <= 0:
                    self.dropped = True
                    self.vy = 0
                    self.angular_velocity = random.uniform(-5, 5)
            
            if self.dropped and not self.settled:
                # Apply gravity with safety checks
                self.vy += GRAVITY * 1.5 * dt
                self.rect.y += int(self.vy)  # Use int for browser compatibility
                self.rect.x += int(self.vx)  # Use int for browser compatibility
                
                # Rotation
                self.rotation += self.angular_velocity
                
                # Check for platform collisions with error handling
                for platform in platforms:
                    try:
                        if self.rect.colliderect(platform.rect):
                            if self.vy > 0:  # Falling down
                                self.rect.bottom = platform.rect.top
                                self.vy = -self.vy * 0.4  # Bounce with damping
                                self.vx *= 0.7  # Friction
                                self.angular_velocity *= 0.7  # Slow rotation
                                
                                # Add impact particles with error handling
                                try:
                                    particles.add_explosion(
                                        (self.rect.centerx, self.rect.bottom),
                                        count=int(abs(self.vy) * 1.5),
                                        color=COLOR_DUST
                                    )
                                except Exception as e:
                                    print(f"Particle error: {e}")
                                
                                self.bounces += 1
                                if self.bounces >= self.max_bounces or abs(self.vy) < 2:
                                    self.settled = True
                                    self.vy = 0
                                    self.vx = 0
                                    self.angular_velocity = 0
                    except Exception as e:
                        print(f"Platform collision error: {e}")
        except Exception as e:
            print(f"FallingStone update error: {e}")
    
    def draw(self, surf, camera_offset):
        draw_pos = (self.rect.x + camera_offset[0], self.rect.y + camera_offset[1])
        
        if self.warning and not self.dropped:
            # Warning indicator
            warn_progress = 1 - (self.warning_timer / self.warning_time)
            warn_color = (255, int(255 * (1 - warn_progress)), 0, int(200 * warn_progress))
            
            # Warning line
            pygame.draw.line(surf, warn_color, 
                           (draw_pos[0] + self.rect.width//2, 0),
                           (draw_pos[0] + self.rect.width//2, draw_pos[1]),
                           3)
            
            # Warning circle
            pygame.draw.circle(surf, warn_color, 
                             (draw_pos[0] + self.rect.width//2, 20),
                             10 + int(5 * math.sin(pygame.time.get_ticks() / 100)))
        
        if self.dropped:
            # Create a rotated stone surface
            stone_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(stone_surf, COLOR_PLATFORM, 
                           (0, 0, self.rect.width, self.rect.height),
                           border_radius=4)
            
            # Add some texture
            pygame.draw.line(stone_surf, COLOR_PLATFORM_EDGE, 
                           (5, 5), (self.rect.width-5, 5), 2)
            pygame.draw.line(stone_surf, COLOR_PLATFORM_EDGE, 
                           (5, self.rect.height-5), (self.rect.width-5, self.rect.height-5), 2)
            
            # Rotate the surface
            rotated_surf = pygame.transform.rotate(stone_surf, self.rotation)
            rotated_rect = rotated_surf.get_rect(center=(draw_pos[0] + self.rect.width//2, 
                                                       draw_pos[1] + self.rect.height//2))
            
            # Draw shadow
            shadow_surf = pygame.transform.rotate(stone_surf, self.rotation)
            shadow_rect = shadow_surf.get_rect(center=(rotated_rect.centerx + 4, rotated_rect.centery + 4))
            shadow_surf.fill((0, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(shadow_surf, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
            
            # Draw stone
            surf.blit(rotated_surf, rotated_rect)

# ---- Enhanced Door ----
class Door:
    def __init__(self, pos1, pos2):
        self.rect1 = pygame.Rect(pos1[0], pos1[1], 40, 60)
        self.rect2 = pygame.Rect(pos2[0], pos2[1], 40, 60)
        self.open = False
        self.trolled_once = False
        self.troll_cooldown = 0
        self.active_rect = self.rect1
        self.glow_phase = 0
    
    def set_open(self):
        self.open = True
    
    def maybe_troll(self, player_rect, particles):
        if self.trolled_once or self.open or self.troll_cooldown > 0:
            return
        
        # Check if player is close to the first door
        if player_rect.colliderect(self.rect1.inflate(60, 60)):
            self.trolled_once = True
            self.troll_cooldown = 2.0
            
            # Swap to the second door position
            self.active_rect = self.rect2
            
            # Add particles at both locations
            particles.add_explosion(self.rect1.center, count=30, color=(100, 100, 255))
            particles.add_explosion(self.rect2.center, count=30, color=(100, 100, 255))
    
    def check_win_collision(self, player_rect):
        if self.open and player_rect.colliderect(self.active_rect):
            return True
        return False
    
    def update(self, dt):
        self.glow_phase += dt * 3
        if self.troll_cooldown > 0:
            self.troll_cooldown -= dt
    
    def draw(self, surf, camera_offset):
        draw_rect = pygame.Rect(
            self.active_rect.x + camera_offset[0],
            self.active_rect.y + camera_offset[1],
            self.active_rect.width,
            self.active_rect.height
        )
        
        # Door shadow
        draw_enhanced_shadow(surf, draw_rect)
        
        # Main door
        door_color = COLOR_DOOR if self.open else COLOR_DOOR_LOCKED
        pygame.draw.rect(surf, door_color, draw_rect, border_radius=8)
        
        # Door frame
        pygame.draw.rect(surf, (door_color[0]+20, door_color[1]+20, door_color[2]+20), 
                       draw_rect, width=2, border_radius=8)
        
        # Door handle
        handle_x = draw_rect.right - 10
        handle_y = draw_rect.centery
        pygame.draw.circle(surf, (200, 200, 200), (handle_x, handle_y), 4)
        
        # Glow effect when open
        if self.open:
            glow_intensity = (math.sin(self.glow_phase) * 0.5 + 0.5) * 150
            glow_surf = pygame.Surface((draw_rect.width + 20, draw_rect.height + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*door_color, int(glow_intensity)), 
                           (10, 10, draw_rect.width, draw_rect.height), border_radius=12)
            surf.blit(glow_surf, (draw_rect.x - 10, draw_rect.y - 10), special_flags=pygame.BLEND_ALPHA_SDL2)

# ---- Enhanced Player ----
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 50)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.facing_right = True
        self.can_double_jump = True
        self.has_double_jumped = False
        self.jump_buffer = 0
        self.coyote_time = 0
        self.dead = False
        self.win = False
        self.blink_timer = 0
        self.squash = 1.0
        self.stretch = 1.0
        # Pre-render player surfaces for better performance
        self.cached_right_surf = None
        self.cached_left_surf = None
        self.create_cached_surfaces()
    
    def control(self, keys, dt):
        if self.dead or self.win:
            return
        
        # Horizontal movement
        move_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x = -1
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x = 1
            self.facing_right = True
        
        # Apply movement with air control
        control_factor = 1.0 if self.on_ground else AIR_CONTROL
        self.vx += move_x * control_factor
        
        # Jump buffer (allows pressing jump slightly before landing)
        if self.jump_buffer > 0:
            self.jump_buffer -= dt
        
        # Coyote time (allows jumping shortly after walking off a platform)
        if self.coyote_time > 0:
            self.coyote_time -= dt
        
        # Jump input
        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]):
            # Regular jump with coyote time
            if self.on_ground or self.coyote_time > 0:
                self.vy = JUMP_VELOCITY
                self.on_ground = False
                self.coyote_time = 0
                self.can_double_jump = True
                self.has_double_jumped = False
                self.squash = 0.7
                self.stretch = 1.3
            # Double jump
            elif self.can_double_jump and not self.has_double_jumped:
                self.vy = DOUBLE_JUMP_VELOCITY
                self.can_double_jump = False
                self.has_double_jumped = True
                self.squash = 0.7
                self.stretch = 1.3
            else:
                # Buffer the jump for a short time
                self.jump_buffer = 0.15
    
    def physics(self, dt, platforms, particles):
        if self.dead or self.win:
            return
        
        # Apply friction/air resistance
        if self.on_ground:
            self.vx *= FRICTION
        else:
            self.vx *= AIR_RESISTANCE
        
        # Limit horizontal speed
        self.vx = max(-MOVE_SPEED, min(MOVE_SPEED, self.vx))
        
        # Apply gravity
        self.vy += GRAVITY
        
        # Terminal velocity
        if self.vy > TERMINAL_VELOCITY:
            self.vy = TERMINAL_VELOCITY
        
        # Horizontal movement and collision
        self.rect.x += self.vx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                    self.vx = 0
                elif self.vx < 0:
                    self.rect.left = platform.rect.right
                    self.vx = 0
        
        # Vertical movement and collision
        was_on_ground = self.on_ground
        self.on_ground = False
        
        self.rect.y += self.vy
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:  # Landing
                    self.rect.bottom = platform.rect.top
                    self.on_ground = True
                    
                    # Execute buffered jump
                    if self.jump_buffer > 0:
                        self.vy = JUMP_VELOCITY
                        self.on_ground = False
                        self.jump_buffer = 0
                        self.can_double_jump = True
                        self.has_double_jumped = False
                        self.squash = 0.7
                        self.stretch = 1.3
                    else:
                        self.vy = 0
                        self.squash = 1.3
                        self.stretch = 0.7
                        
                        # Landing particles
                        if abs(self.vy) > 2:
                            particles.add_dust((self.rect.centerx, self.rect.bottom), count=int(abs(self.vy)/2))
                elif self.vy < 0:  # Hitting ceiling
                    self.rect.top = platform.rect.bottom
                    self.vy = 0
        
        # Start coyote time when walking off a platform
        if was_on_ground and not self.on_ground:
            self.coyote_time = 0.1
        
        # Squash and stretch animation
        self.squash += (1.0 - self.squash) * 0.2
        self.stretch += (1.0 - self.stretch) * 0.2
        
        # Blink timer
        if self.blink_timer > 0:
            self.blink_timer -= dt
    
    def create_cached_surfaces(self):
        """Pre-render player surfaces for better performance"""
        # Create normal player surface
        normal_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(normal_surf, COLOR_PLAYER, (0, 0, self.rect.width, self.rect.height), border_radius=10)
        
        # Create eyes for right-facing
        eye_y = self.rect.height // 3
        eye_size = max(4, self.rect.width // 6)
        left_eye_x = self.rect.width // 3 - eye_size // 2
        right_eye_x = self.rect.width * 2 // 3 - eye_size // 2
        
        pygame.draw.rect(normal_surf, (0, 0, 0), (left_eye_x, eye_y, eye_size, eye_size))
        pygame.draw.rect(normal_surf, (0, 0, 0), (right_eye_x, eye_y, eye_size, eye_size))
        
        # Store the surfaces
        self.cached_right_surf = normal_surf
        
        # Create left-facing surface (flipped)
        self.cached_left_surf = pygame.transform.flip(normal_surf, True, False)
        
        # Create dead and win surfaces too
        self.cached_dead_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(self.cached_dead_surf, (150, 50, 50), (0, 0, self.rect.width, self.rect.height), border_radius=10)
        
        # X eyes
        pygame.draw.line(self.cached_dead_surf, (0, 0, 0), (left_eye_x, eye_y), 
                       (left_eye_x + eye_size, eye_y + eye_size), 2)
        pygame.draw.line(self.cached_dead_surf, (0, 0, 0), (left_eye_x + eye_size, eye_y), 
                       (left_eye_x, eye_y + eye_size), 2)
        pygame.draw.line(self.cached_dead_surf, (0, 0, 0), (right_eye_x, eye_y), 
                       (right_eye_x + eye_size, eye_y + eye_size), 2)
        pygame.draw.line(self.cached_dead_surf, (0, 0, 0), (right_eye_x + eye_size, eye_y), 
                       (right_eye_x, eye_y + eye_size), 2)
        
        # Win surface
        self.cached_win_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(self.cached_win_surf, (100, 200, 100), (0, 0, self.rect.width, self.rect.height), border_radius=10)
        
        # Happy eyes
        pygame.draw.arc(self.cached_win_surf, (0, 0, 0), 
                      (left_eye_x, eye_y, eye_size, eye_size),
                      math.pi, 2*math.pi, 2)
        pygame.draw.arc(self.cached_win_surf, (0, 0, 0), 
                      (right_eye_x, eye_y, eye_size, eye_size),
                      math.pi, 2*math.pi, 2)
        
        # Blink surface
        self.cached_blink_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(self.cached_blink_surf, COLOR_PLAYER, (0, 0, self.rect.width, self.rect.height), border_radius=10)
        
        # Blinking eyes
        pygame.draw.line(self.cached_blink_surf, (0, 0, 0), 
                       (left_eye_x, eye_y + eye_size//2), 
                       (left_eye_x + eye_size, eye_y + eye_size//2), 2)
        pygame.draw.line(self.cached_blink_surf, (0, 0, 0), 
                       (right_eye_x, eye_y + eye_size//2), 
                       (right_eye_x + eye_size, eye_y + eye_size//2), 2)
        
        # Flipped blink surface
        self.cached_blink_left_surf = pygame.transform.flip(self.cached_blink_surf, True, False)
    
    def draw(self, surf, camera_offset):
        # Calculate draw position
        draw_x = self.rect.x + camera_offset[0]
        draw_y = self.rect.y + camera_offset[1]
        
        # Apply squash and stretch
        width = int(self.rect.width * self.stretch)
        height = int(self.rect.height * self.squash)
        x_offset = (width - self.rect.width) // 2
        y_offset = (height - self.rect.height)
        
        draw_rect = pygame.Rect(draw_x - x_offset, draw_y - y_offset, width, height)
        
        # Draw shadow (simplified)
        shadow_rect = pygame.Rect(draw_rect.x + 4, draw_rect.y + 4, draw_rect.width, draw_rect.height)
        pygame.draw.rect(surf, COLOR_PLAYER_SHADOW, shadow_rect, border_radius=10)
        
        # Select the appropriate cached surface
        if self.dead:
            player_surf = self.cached_dead_surf
        elif self.win:
            player_surf = self.cached_win_surf
        elif self.blink_timer > 0:
            player_surf = self.cached_blink_left_surf if not self.facing_right else self.cached_blink_surf
        else:
            player_surf = self.cached_left_surf if not self.facing_right else self.cached_right_surf
        
        # Scale the surface according to squash and stretch
        scaled_surf = pygame.transform.scale(player_surf, (width, height))
        
        # Draw the player
        surf.blit(scaled_surf, (draw_rect.x, draw_rect.y))
        
        # Randomly blink (reduced probability for better performance)
        if random.random() < 0.002 and self.blink_timer <= 0:
            self.blink_timer = 0.1

# ---- Game Class ----
class Game:
    def __init__(self):
        self.state = GameState.PLAYING
        self.start_time = time.time()
        self.death_time = None
        self.win_time = None
        self.attempts = 1
        self.best_time = float('inf')
        
        # Initialize systems
        self.particles = ParticleSystem()
        self.camera = Camera()
        
        # Setup level
        self.setup_level()
    
    def setup_level(self):
        """Create a challenging but completable level with some traps"""
        self.platforms = []
        
        # Ground and main platforms - wider and more forgiving
        self.platforms.append(Platform(0, HEIGHT-50, WIDTH, 50))  # Ground
        self.platforms.append(Platform(120, HEIGHT-160, 220, 20))  # First ledge (wider)
        self.platforms.append(Platform(400, HEIGHT-240, 180, 20))  # Mid platform (wider)
        self.platforms.append(Platform(640, HEIGHT-320, 200, 20))  # High platform (wider)
        self.platforms.append(Platform(900, HEIGHT-200, 220, 20))  # Right platform (wider)
        self.platforms.append(Platform(1100, HEIGHT-280, 140, 20)) # Final approach (wider)
        
        # Additional challenge platforms - more reasonable sizes
        self.platforms.append(Platform(300, HEIGHT-120, 80, 16))   # Stepping stone (wider)
        self.platforms.append(Platform(580, HEIGHT-160, 60, 16))   # Gap bridge (wider)
        self.platforms.append(Platform(820, HEIGHT-240, 70, 16))   # Precision jump (wider)
        
        # Fewer fake platforms with longer delay before disappearing
        self.fake_platforms = [
            FakePlatform(220, HEIGHT-200, 60, 16, delay=0.8),  # Early trap (longer delay)
            FakePlatform(750, HEIGHT-260, 50, 16, delay=0.7),  # High-level trap (longer delay)
        ]
        
        # Magic wall - now requires multiple hits
        self.magic_wall = MagicWall(350, HEIGHT-140, 70, 80)
        
        # Fewer spikes with more reasonable patterns and delays
        self.spikes = [
            Spike(180, HEIGHT-178, w=32, h=26, popup=False),  # Static warning
            Spike(450, HEIGHT-258, w=32, h=26, popup=True, delay=1.5),  # Slower popup
            Spike(700, HEIGHT-338, w=32, h=26, popup=False, 
                  move_pattern={'type': 'horizontal', 'speed': 2, 'range': 60}),  # Slower moving
            Spike(950, HEIGHT-218, w=32, h=26, popup=True, delay=1.2),  # Slower popup
            # Only one surprise spike
            Spike(580, HEIGHT-178, w=32, h=26, popup=True, delay=0.8),  # More reasonable surprise
        ]
        
        # Fewer falling stones with longer warning times
        self.falling_stones = [
            FallingStone(480, 50, trigger_range=(420, 540), warning_time=1.5),
            FallingStone(680, 30, trigger_range=(600, 720), warning_time=1.2),
            FallingStone(980, 40, trigger_range=(920, 1020), warning_time=1.0),
            # Only one surprise stone
            FallingStone(350, 40, trigger_range=(300, 400), warning_time=0.8),
        ]
        
        # Only one teleport trap with a more forgiving destination
        self.teleport_traps = [
            TeleportTrap(900, HEIGHT-220, 30, 10, dest=(600, HEIGHT-340)),  # To platform
        ]
        
        # Enhanced door with proper collision - only one fake door
        self.door = Door(pos1=(1140, HEIGHT-340), pos2=(160, HEIGHT-220))
        self.fake_doors = [
            FakeDoor(500, HEIGHT-260),  # One fake door
        ]
        
        # Win trigger - must reach the end area
        self.win_trigger = pygame.Rect(WIDTH-60, 0, 60, HEIGHT)
        
        # Player
        self.player = Player(60, HEIGHT-100)
    
    def handle_collisions(self):
        """Optimized collision detection with browser-safe implementation"""
        if self.state != GameState.PLAYING:
            return
        
        # Use a single try-except block for better performance
        try:
            # Early exit flag to avoid unnecessary checks after player death
            player_killed = False
            
            # Wall collision - now requires multiple hits
            if (not player_killed and self.magic_wall.alive and 
                self.player.rect.colliderect(self.magic_wall.rect.inflate(5, 5))):
                
                if self.magic_wall.hit():  # Wall destroyed
                    self.particles.add_explosion(
                        self.magic_wall.rect.center, 
                        count=10,  # Reduced particle count
                        color=COLOR_WALL_CRACK
                    )
                    self.camera.add_shake(6, 0.4)  # Reduced shake
                else:  # Wall damaged
                    self.particles.add_explosion(
                        (self.player.rect.centerx, self.magic_wall.rect.centery),
                        count=5,  # Reduced particle count
                        color=COLOR_WALL_CRACK
                    )
                    self.camera.add_shake(3, 0.2)  # Reduced shake
            
            # Fake platform collisions
            if not player_killed:
                for platform in self.fake_platforms:
                    if platform.active and not platform.triggered and self.player.rect.colliderect(platform.rect):
                        if self.player.vy > 0:  # Only trigger when landing on it
                            platform.trigger()
                            # Small camera shake as feedback
                            self.camera.add_shake(1, 0.1)  # Reduced shake
            
            # Teleport trap collisions
            if not player_killed:
                for trap in self.teleport_traps:
                    new_pos = trap.check_teleport(self.player.rect, self.particles)
                    if new_pos:
                        self.player.rect.x = new_pos[0]
                        self.player.rect.y = new_pos[1]
                        self.player.vx = 0
                        self.player.vy = 0
                        self.camera.add_shake(3, 0.3)  # Reduced camera effect
                        break  # Only allow one teleport at a time
            
            # Fake door collisions
            if not player_killed:
                for door in self.fake_doors:
                    if door.check_collision(self.player.rect):
                        self.kill_player()
                        player_killed = True
                        break
            
            # Spike collisions - simplified collision detection
            if not player_killed:
                for spike in self.spikes:
                    danger_zone = spike.get_danger_zone()
                    if danger_zone and self.point_in_triangle_collision(self.player.rect, danger_zone):
                        self.kill_player()
                        player_killed = True
                        break
            
            # Falling stone collisions - simplified
            if not player_killed:
                for stone in self.falling_stones:
                    if stone.rect.colliderect(self.player.rect):
                        self.kill_player()
                        player_killed = True
                        break
            
            # Door interactions - only if player still alive
            if not player_killed:
                self.door.maybe_troll(self.player.rect, self.particles)
            
            # Win condition - check if door is open and proper collision
            if not player_killed:
                if self.player.rect.colliderect(self.win_trigger):
                    self.door.set_open()
                
                if self.door.check_win_collision(self.player.rect):
                    self.win_game()
                    
        except Exception as e:
            # Single exception handler for all collision checks
            print(f"Collision handling error: {e}")
    
    def point_in_triangle_collision(self, rect, triangle_points):
        """Check if rectangle overlaps with triangle - browser-safe implementation"""
        try:
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
        except Exception as e:
            print(f"Triangle collision error: {e}")
            return False  # Safer to return false on error
    
    def point_in_triangle(self, point, triangle):
        """Check if point is inside triangle using barycentric coordinates - with safety checks"""
        try:
            # Validate inputs to prevent browser crashes
            if not point or not triangle or len(triangle) != 3:
                return False
                
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
        except Exception as e:
            print(f"Point in triangle calculation error: {e}")
            return False  # Safer to return false on error
    
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
        
        # Get player position once for distance checks
        player_x = self.player.rect.centerx
        player_y = self.player.rect.centery
        
        # Update fake platforms - only if they're visible
        try:
            for platform in self.fake_platforms:
                # Only update platforms within 800 pixels of player
                if abs(platform.rect.centerx - player_x) < 800:
                    platform.update(dt)
        except Exception as e:
            print(f"Fake platform update error: {e}")
        
        # Update teleport traps - only if they're visible
        try:
            for trap in self.teleport_traps:
                # Only update traps within 800 pixels of player
                if abs(trap.rect.centerx - player_x) < 800:
                    trap.update(dt)
        except Exception as e:
            print(f"Teleport trap update error: {e}")
        
        # Update fake doors - only if they're visible
        try:
            for door in self.fake_doors:
                # Only update doors within 800 pixels of player
                if abs(door.rect.centerx - player_x) < 800:
                    door.update(dt)
        except Exception as e:
            print(f"Fake door update error: {e}")
        
        # Physics for all objects - optimize platform collision list
        # Only include platforms that are near the player
        platforms_for_collision = [p for p in self.platforms if abs(p.rect.centerx - player_x) < 800]
        
        # Add active fake platforms to collision list - only if they're near the player
        try:
            for fake in self.fake_platforms:
                if fake.active and not fake.triggered and abs(fake.rect.centerx - player_x) < 800:
                    platforms_for_collision.append(Platform(fake.rect.x, fake.rect.y,
                                                          fake.rect.width, fake.rect.height))
        except Exception as e:
            print(f"Fake platform collision setup error: {e}")
            
        # Only add magic wall if it's alive and near the player
        if self.magic_wall.alive and abs(self.magic_wall.rect.centerx - player_x) < 800:
            platforms_for_collision.append(Platform(self.magic_wall.rect.x, self.magic_wall.rect.y,
                                                   self.magic_wall.rect.width, self.magic_wall.rect.height))
        
        # Physics update with optimized platform list
        self.player.physics(dt, platforms_for_collision, self.particles)
        
        # Update other objects - only if they're visible
        for spike in self.spikes:
            # Only update spikes within 800 pixels of player
            if abs(spike.rect.centerx - player_x) < 800:
                spike.update(dt)
        
        for stone in self.falling_stones:
            # Only check and update stones within 1000 pixels of player
            if abs(stone.rect.centerx - player_x) < 1000:
                stone.trigger_check(player_x)
                stone.update(dt, platforms_for_collision, self.particles)  # Use optimized platform list
        
        # Only update magic wall if it's near the player
        if abs(self.magic_wall.rect.centerx - player_x) < 800:
            self.magic_wall.update(dt)
            
        # Always update the door as it's important for game progression
        self.door.update(dt)
        
        # Update systems - with optimizations
        self.particles.update(dt)
        
        # Smoother camera with less computation
        self.camera.follow(self.player.rect, smooth=0.15)  # Slightly smoother
        self.camera.update(dt)
        
        # Collision detection
        self.handle_collisions()
        
        return True
    
    def draw(self, surf):
        # Clear screen
        surf.fill((0, 0, 0))
        
        # Background gradient
        draw_vertical_gradient(surf, COLOR_BG_TOP, COLOR_BG_BOTTOM)
        
        # Atmospheric effects - only draw every other frame
        if pygame.time.get_ticks() % 2 == 0:
            self.draw_atmosphere(surf)
        
        # Get camera offset once
        camera_offset = self.camera.get_offset()
        
        # Get player position for culling
        player_x = self.player.rect.centerx
        player_y = self.player.rect.centery
        
        # Calculate visible area with some margin
        visible_left = player_x - WIDTH//2 - 100 - camera_offset[0]
        visible_right = player_x + WIDTH//2 + 100 - camera_offset[0]
        visible_top = player_y - HEIGHT//2 - 100 - camera_offset[1]
        visible_bottom = player_y + HEIGHT//2 + 100 - camera_offset[1]
        
        # Draw game objects - only if they're visible
        for platform in self.platforms:
            # Only draw platforms that are potentially visible
            if (platform.rect.right > visible_left and 
                platform.rect.left < visible_right and
                platform.rect.bottom > visible_top and
                platform.rect.top < visible_bottom):
                platform.draw(surf, camera_offset)
            
        # Draw fake platforms - only if they're visible
        try:
            for platform in self.fake_platforms:
                # Only draw platforms that are potentially visible
                if (platform.rect.right > visible_left and 
                    platform.rect.left < visible_right and
                    platform.rect.bottom > visible_top and
                    platform.rect.top < visible_bottom):
                    platform.draw(surf, camera_offset)
        except Exception as e:
            print(f"Fake platform draw error: {e}")
        
        # Draw teleport traps - only if they're visible
        try:
            for trap in self.teleport_traps:
                # Only draw traps that are potentially visible
                if (trap.rect.right > visible_left and 
                    trap.rect.left < visible_right and
                    trap.rect.bottom > visible_top and
                    trap.rect.top < visible_bottom):
                    trap.draw(surf, camera_offset)
        except Exception as e:
            print(f"Teleport trap draw error: {e}")
        
        # Draw magic wall - only if it's visible
        if (self.magic_wall.rect.right > visible_left and 
            self.magic_wall.rect.left < visible_right and
            self.magic_wall.rect.bottom > visible_top and
            self.magic_wall.rect.top < visible_bottom):
            self.magic_wall.draw(surf, camera_offset)
        
        # Draw spikes - only if they're visible
        for spike in self.spikes:
            if (spike.rect.right > visible_left and 
                spike.rect.left < visible_right and
                spike.rect.bottom > visible_top and
                spike.rect.top < visible_bottom):
                spike.draw(surf, camera_offset)
        
        # Draw falling stones - only if they're visible
        for stone in self.falling_stones:
            if (stone.rect.right > visible_left and 
                stone.rect.left < visible_right and
                stone.rect.bottom > visible_top and
                stone.rect.top < visible_bottom):
                stone.draw(surf, camera_offset)
        
        # Always draw the door as it's important for game progression
        self.door.draw(surf, camera_offset)
        
        # Draw fake doors - only if they're visible
        try:
            for door in self.fake_doors:
                if (door.rect.right > visible_left and 
                    door.rect.left < visible_right and
                    door.rect.bottom > visible_top and
                    door.rect.top < visible_bottom):
                    door.draw(surf, camera_offset)
        except Exception as e:
            print(f"Fake door draw error: {e}")
            
        # Always draw the player
        self.player.draw(surf, camera_offset)
        
        # Draw particles
        self.particles.draw(surf)
        
        # UI - always draw
        self.draw_ui(surf)
    
    def draw_atmosphere(self, surf):
        """Draw atmospheric effects - optimized version"""
        # Only update atmosphere every other frame to reduce CPU usage
        if pygame.time.get_ticks() % 2 == 0:
            return
            
        t = pygame.time.get_ticks() / 1000.0
        
        # Reduced fog layers (2 instead of 4)
        for i in range(2):
            y = int(100 + i * 120 + math.sin(t * 0.3 + i) * 20)
            alpha = 30 + int(20 * math.sin(t * 0.5 + i))
            
            # Use a smaller fog surface
            fog_surf = pygame.Surface((WIDTH + 100, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(fog_surf, (255, 255, 255, alpha), (0, 0, WIDTH + 100, 60))
            surf.blit(fog_surf, (-50 + i * 30, y), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Reduced parallax elements (3 instead of 6)
        for i in range(3):
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
async def main():
    game = Game()
    running = True
    last_time = time.time()
    
    while running:
        try:
            # Calculate delta time with a safety cap to prevent large jumps
            current_time = time.time()
            dt = min(clock.tick(FPS) / 1000.0, 0.1)  # Cap at 100ms to prevent physics issues
            last_time = current_time
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Get keys
            keys = pygame.key.get_pressed()
            
            # Update game with error handling
            try:
                if not game.update(dt, keys):
                    running = False
            except Exception as e:
                print(f"Game update error: {e}")
            
            # Draw everything with error handling
            try:
                game.draw(screen)
                pygame.display.flip()
            except Exception as e:
                print(f"Game draw error: {e}")
            
            # Give control back to browser - essential for web version
            await asyncio.sleep(0)
        except Exception as e:
            print(f"Main loop error: {e}")
            # Don't exit on error, try to continue
            await asyncio.sleep(0.1)
    
    pygame.quit()
    return 0

if __name__== "__main__":
    if sys.platform == "emscripten":
        # Set pixelated rendering for better look on web
        import platform
        platform.window.canvas.style.imageRendering = "pixelated"
        
    asyncio.run(main())