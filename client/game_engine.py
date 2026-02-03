import pygame
import random
import json
import os
import math
import time

TILE_SIZE = 64
CHUNK_SIZE = 16 # tiles per chunk axis (16x16)

class DayNightCycle:
    def __init__(self, screen_width, screen_height):
        self.time = 12.0 # 0-24
        self.speed = 1.0 # Real seconds per game hour (tuned for play)
        self.width = screen_width
        self.height = screen_height
        self.overlay = pygame.Surface((screen_width, screen_height))
        self.color = (0, 0, 50) # Deep blue night
        
    def update(self, dt):
        self.time += dt * self.speed
        if self.time >= 24: self.time = 0
        
    def get_darkness(self):
        # 6-18 is day (alpha 0). 18-6 is night (alpha ramps to 200).
        alpha = 0
        if 18 <= self.time < 20: # Dusk
            alpha = (self.time - 18) / 2 * 150
        elif 20 <= self.time < 5: # Night
            alpha = 180
        elif 5 <= self.time < 7: # Dawn
            alpha = 180 - (self.time - 5) / 2 * 180
            
        self.overlay.set_alpha(int(alpha))
        self.overlay.fill(self.color)
        return self.overlay, int(alpha)

class Vegetation:
    def __init__(self, x, y, type_name):
        self.x = x
        self.y = y
        self.type = type_name # 'tree', 'flower'
        self.sway_offset = random.uniform(0, 6.28) # Random phase

class Chunk:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.tiles = {} # (x, y) -> tile_type
        self.vegetation = [] # List of Vegetation
        self.generate()

    def generate(self):
        # varied generation
        for y in range(CHUNK_SIZE):
            for x in range(CHUNK_SIZE):
                # Global coords
                gx = self.cx * CHUNK_SIZE + x
                gy = self.cy * CHUNK_SIZE + y
                
                # Simple perlin-ish noise stand-in
                val = (math.sin(gx * 0.1) + math.cos(gy * 0.1) + 2) * 20
                
                if val < 5:
                    self.tiles[(x, y)] = "water"
                elif val < 15:
                    self.tiles[(x, y)] = "dirt"
                else:
                    self.tiles[(x, y)] = "grass"
                    # Chance for veg
                    if random.random() < 0.05:
                        self.vegetation.append(Vegetation(gx, gy, 'tree'))
                    elif random.random() < 0.2:
                        self.vegetation.append(Vegetation(gx, gy, 'flower'))

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.zoom_level = 1.0
        self.target_zoom = 1.0

    def set_zoom(self, value):
        self.target_zoom = max(0.5, min(2.0, value)) # Clamp zoom 0.5x to 2x

    def update_zoom(self):
        # Smooth zoom
        if abs(self.target_zoom - self.zoom_level) > 0.01:
             self.zoom_level += (self.target_zoom - self.zoom_level) * 0.1

    def apply(self, entity_rect):
        # Simple rect offset - logic needs to handle zoom if using rects for rendering
        # For now, we prefer apply_pos for drawing
        return entity_rect.move(self.camera.topleft)

    def apply_pos(self, x, y):
        # Apply scaling around center
        # (x - cam_x) * zoom + center_x
        
        # Camera rect x,y is topleft, but we want center based
        
        # Better: Standard cam offset first, then zoom relative to screen center
        
        cx, cy = self.width // 2, self.height // 2
        
        # Relative to camera top left (which is usually player pos logic inverse)
        # We need world relative to camera center
        # Let's trust self.camera property is set correctly in update()
        
        # ScreenX = (WorldX + CameraX) * Zoom + CenterOffset? 
        # No, update() sets camera to: -target + screen_center
        # So (WorldX + CameraX) gives position relative to screen top-left (0,0) where 0,0 is the center of view if target is at 0,0 locally
        
        rel_x = x + self.camera.x
        rel_y = y + self.camera.y
        
        # But we want to zoom around the center of the screen
        # So we shift to center relative, scale, then shift back
        
        # Actually simplest is:
        # ScreenX = (RelX - CenterX) * Zoom + CenterX
        
        # Wait, self.camera.x/y already centers the target on (Width/2, Height/2)
        # So at the player position, rel_x should be Width/2.
        
        final_x = (rel_x - cx) * self.zoom_level + cx
        final_y = (rel_y - cy) * self.zoom_level + cy
        
        return int(final_x), int(final_y)

    def update(self, target):
        self.update_zoom()
        # target can be a rect or pos
        x = -target[0] + int(self.width / 2)
        y = -target[1] + int(self.height / 2)
        self.camera = pygame.Rect(x, y, self.width, self.height)

# Duplicate Chunk class removed

class Firefly:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.float_offset = random.uniform(0, 100)
        self.color = (200, 255, 100) # Greenish yellow
        self.size = random.randint(2, 4)
        
    def update(self, dt):
        # Float around
        self.x += math.sin(time.time() + self.float_offset) * 0.5
        self.y += math.cos(time.time() * 0.5 + self.float_offset) * 0.5

class Map:
    def __init__(self, screen_width, screen_height):
        self.chunks = {} # (cx, cy) -> Chunk
        self.assets = {} # Loaded explicitly later

    def load_assets(self):
        # Load assets
        try:
            self.assets['grass'] = pygame.image.load("assets/tiles/grass.png").convert()
            self.assets['dirt'] = pygame.image.load("assets/tiles/dirt.png").convert()
            self.assets['water'] = pygame.image.load("assets/tiles/water.png").convert()
            # Vegetation
            self.assets['tree'] = pygame.image.load("assets/tiles/tree.png").convert_alpha()
            self.assets['flower'] = pygame.image.load("assets/tiles/flower_grass.png").convert_alpha()
            
            # Scale if needed, assuming 64x64 for tiles
            for k in ['grass', 'dirt', 'water']:
                self.assets[k] = pygame.transform.scale(self.assets[k], (TILE_SIZE, TILE_SIZE))
        except Exception as e:
            print(f"Error loading tiles: {e}")
            # Fallback colors
            self.assets['grass'] = (50, 200, 50)
            self.assets['dirt'] = (150, 100, 50)
            self.assets['water'] = (50, 50, 200)
            self.assets['tree'] = (0, 100, 0)
            self.assets['flower'] = (255, 255, 0)

    def get_chunk(self, cx, cy):
        if (cx, cy) not in self.chunks:
            self.chunks[(cx, cy)] = Chunk(cx, cy)
        return self.chunks[(cx, cy)]

    def draw(self, screen, camera):
        # Determine visible chunks with zoom
        # Effective tile size
        eff_tile = int(TILE_SIZE * camera.zoom_level)
        if eff_tile < 1: eff_tile = 1
        
        # Inverse view to get world bounds
        # Screen (0,0) -> World ?
        # x_screen = (x_world + cam_x - cx) * zoom + cx
        # x_world = ((x_screen - cx) / zoom) + cx - cam_x
        
        cx_scr, cy_scr = camera.width // 2, camera.height // 2
        
        def screen_to_world(sx, sy):
            wx = ((sx - cx_scr) / camera.zoom_level) + cx_scr - camera.camera.x
            wy = ((sy - cy_scr) / camera.zoom_level) + cy_scr - camera.camera.y
            return wx, wy

        min_wx, min_wy = screen_to_world(0, 0)
        max_wx, max_wy = screen_to_world(camera.width, camera.height)
        
        start_tx = int(min_wx // TILE_SIZE) - 1
        start_ty = int(min_wy // TILE_SIZE) - 1
        end_tx = int(max_wx // TILE_SIZE) + 1
        end_ty = int(max_wy // TILE_SIZE) + 1
        
        # Convert to chunks
        start_cx = start_tx // CHUNK_SIZE
        start_cy = start_ty // CHUNK_SIZE
        end_cx = end_tx // CHUNK_SIZE
        end_cy = end_ty // CHUNK_SIZE

        for cy in range(start_cy, end_cy + 1):
            for cx in range(start_cx, end_cx + 1):
                chunk = self.get_chunk(cx, cy)
                
                for (lx, ly), t_type in chunk.tiles.items():
                    gx = (cx * CHUNK_SIZE + lx) * TILE_SIZE
                    gy = (cy * CHUNK_SIZE + ly) * TILE_SIZE
                    
                    scr_x, scr_y = camera.apply_pos(gx, gy)
                    
                    # Size
                    scaled_size = int(TILE_SIZE * camera.zoom_level)
                    # Optimization: Don't draw if tiny or offscreen (already Culled roughly by block loop)
                    if -scaled_size < scr_x < camera.width and -scaled_size < scr_y < camera.height:
                         asset = self.assets.get(t_type)
                         if isinstance(asset, pygame.Surface):
                             # Scale on fly? Expensive. But good for zoom. 
                             s = pygame.transform.scale(asset, (scaled_size + 1, scaled_size + 1)) 
                             screen.blit(s, (scr_x, scr_y))
                         else:
                             pygame.draw.rect(screen, asset, (scr_x, scr_y, scaled_size, scaled_size))
                             
                # Draw Vegetation (Simple, unsorted for now. Ideally should be sorted by Y with entities)
                # We will handle vegetation later in main loop for Y-sort?
                # Actually, Map.draw usually draws ground. 
                # Let's add a method get_visible_vegetation(camera) to main for proper Y-sorting
                
    def get_visible_vegetation(self, camera):
        visible = []
        # Same chunk logic
        cx_scr, cy_scr = camera.width // 2, camera.height // 2
        def screen_to_world(sx, sy):
            wx = ((sx - cx_scr) / camera.zoom_level) + cx_scr - camera.camera.x
            wy = ((sy - cy_scr) / camera.zoom_level) + cy_scr - camera.camera.y
            return wx, wy

        min_wx, min_wy = screen_to_world(0, 0)
        max_wx, max_wy = screen_to_world(camera.width, camera.height)
        
        start_cx = int(min_wx // TILE_SIZE // CHUNK_SIZE) - 1
        start_cy = int(min_wy // TILE_SIZE // CHUNK_SIZE) - 1
        end_cx = int(max_wx // TILE_SIZE // CHUNK_SIZE) + 1
        end_cy = int(max_wy // TILE_SIZE // CHUNK_SIZE) + 1
        
        for cy in range(start_cy, end_cy + 1):
            for cx in range(start_cx, end_cx + 1):
                chunk = self.get_chunk(cx, cy)
                for veg in chunk.vegetation:
                     visible.append(veg)
        return visible

class InputManager:
    def __init__(self):
        self.bindings = {
            "MOVE_UP": pygame.K_w,
            "MOVE_DOWN": pygame.K_s,
            "MOVE_LEFT": pygame.K_a,
            "MOVE_RIGHT": pygame.K_d,
            "PAUSE": pygame.K_ESCAPE
        }
        self.load()

    def load(self):
        if os.path.exists("keybindings.json"):
            try:
                with open("keybindings.json", "r") as f:
                    saved = json.load(f)
                    # Convert values back to int if needed, though json handles ints
                    self.bindings.update(saved)
            except:
                pass

    def save(self):
        with open("keybindings.json", "w") as f:
            json.dump(self.bindings, f)

    def is_pressed(self, action):
        keys = pygame.key.get_pressed()
        return keys[self.bindings[action]]

    def get_key_name(self, action):
        return pygame.key.name(self.bindings[action])
