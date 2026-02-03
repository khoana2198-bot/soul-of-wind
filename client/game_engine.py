 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/client/game_engine.py b/client/game_engine.py
index 6cda1dd74af459487b636fcd6a614326bdb12c37..6020dcd2841aa9cba9c2ee4d0c873a5ae7d14c94 100644
--- a/client/game_engine.py
+++ b/client/game_engine.py
@@ -129,135 +129,152 @@ class Camera:
         
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
 
-class Map:
-    def __init__(self, screen_width, screen_height):
-        self.chunks = {} # (cx, cy) -> Chunk
-        self.assets = {} # Loaded explicitly later
+class Map:
+    def __init__(self, screen_width, screen_height):
+        self.chunks = {} # (cx, cy) -> Chunk
+        self.assets = {} # Loaded explicitly later
+        self.scale_cache = {}
 
-    def load_assets(self):
-        # Load assets
-        try:
-            self.assets['grass'] = pygame.image.load("assets/tiles/grass.png").convert()
-            self.assets['dirt'] = pygame.image.load("assets/tiles/dirt.png").convert()
-            self.assets['water'] = pygame.image.load("assets/tiles/water.png").convert()
-            # Vegetation
-            self.assets['tree'] = pygame.image.load("assets/tiles/tree.png").convert_alpha()
-            self.assets['flower'] = pygame.image.load("assets/tiles/flower_grass.png").convert_alpha()
+    def load_assets(self):
+        # Load assets
+        try:
+            self.assets['grass'] = pygame.image.load("assets/tiles/grass.png").convert()
+            self.assets['dirt'] = pygame.image.load("assets/tiles/dirt.png").convert()
+            self.assets['water'] = pygame.image.load("assets/tiles/water.png").convert()
+            # Vegetation
+            self.assets['tree'] = pygame.image.load("assets/tiles/tree.png").convert_alpha()
+            self.assets['flower'] = pygame.image.load("assets/tiles/flower_grass.png").convert_alpha()
             
             # Scale if needed, assuming 64x64 for tiles
             for k in ['grass', 'dirt', 'water']:
                 self.assets[k] = pygame.transform.scale(self.assets[k], (TILE_SIZE, TILE_SIZE))
-        except Exception as e:
-            print(f"Error loading tiles: {e}")
-            # Fallback colors
-            self.assets['grass'] = (50, 200, 50)
-            self.assets['dirt'] = (150, 100, 50)
-            self.assets['water'] = (50, 50, 200)
-            self.assets['tree'] = (0, 100, 0)
-            self.assets['flower'] = (255, 255, 0)
-
-    def get_chunk(self, cx, cy):
-        if (cx, cy) not in self.chunks:
-            self.chunks[(cx, cy)] = Chunk(cx, cy)
-        return self.chunks[(cx, cy)]
+        except Exception as e:
+            print(f"Error loading tiles: {e}")
+            # Fallback colors
+            self.assets['grass'] = (50, 200, 50)
+            self.assets['dirt'] = (150, 100, 50)
+            self.assets['water'] = (50, 50, 200)
+            self.assets['tree'] = (0, 100, 0)
+            self.assets['flower'] = (255, 255, 0)
+
+    def get_scaled_asset(self, key, size):
+        asset = self.assets.get(key)
+        if not isinstance(asset, pygame.Surface):
+            return asset
+        cache_key = (key, size)
+        if cache_key not in self.scale_cache:
+            self.scale_cache[cache_key] = pygame.transform.smoothscale(asset, (size, size))
+        return self.scale_cache[cache_key]
+
+    def get_scaled_surface(self, key, size):
+        asset = self.assets.get(key)
+        if not isinstance(asset, pygame.Surface):
+            return asset
+        cache_key = (key, size[0], size[1])
+        if cache_key not in self.scale_cache:
+            self.scale_cache[cache_key] = pygame.transform.smoothscale(asset, size)
+        return self.scale_cache[cache_key]
+
+    def get_chunk(self, cx, cy):
+        if (cx, cy) not in self.chunks:
+            self.chunks[(cx, cy)] = Chunk(cx, cy)
+        return self.chunks[(cx, cy)]
 
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
                     
-                    # Size
-                    scaled_size = int(TILE_SIZE * camera.zoom_level)
-                    # Optimization: Don't draw if tiny or offscreen (already Culled roughly by block loop)
-                    if -scaled_size < scr_x < camera.width and -scaled_size < scr_y < camera.height:
-                         asset = self.assets.get(t_type)
-                         if isinstance(asset, pygame.Surface):
-                             # Scale on fly? Expensive. But good for zoom. 
-                             s = pygame.transform.scale(asset, (scaled_size + 1, scaled_size + 1)) 
-                             screen.blit(s, (scr_x, scr_y))
-                         else:
-                             pygame.draw.rect(screen, asset, (scr_x, scr_y, scaled_size, scaled_size))
+                    # Size
+                    scaled_size = int(TILE_SIZE * camera.zoom_level)
+                    # Optimization: Don't draw if tiny or offscreen (already Culled roughly by block loop)
+                    if -scaled_size < scr_x < camera.width and -scaled_size < scr_y < camera.height:
+                         asset = self.get_scaled_asset(t_type, scaled_size + 1)
+                         if isinstance(asset, pygame.Surface):
+                             screen.blit(asset, (scr_x, scr_y))
+                         else:
+                             pygame.draw.rect(screen, asset, (scr_x, scr_y, scaled_size, scaled_size))
                              
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
 
EOF
)
