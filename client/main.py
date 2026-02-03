 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/client/main.py b/client/main.py
index 265c18af85112639d30a70c06f767574df1f8780..e42764c26827802590f41f930e34ae6aa3abf2d1 100644
--- a/client/main.py
+++ b/client/main.py
@@ -32,141 +32,165 @@ logging.info("Starting game client...")
 # --- Constants ---
 SCREEN_WIDTH = 800
 SCREEN_HEIGHT = 600
 FPS = 60
 BG_COLOR = (30, 30, 30)
 PLAYER_COLOR = (100, 200, 100)
 SERVER_IP = '127.0.0.1'
 SERVER_PORT = 5555
 
 class GameClient:
     def __init__(self):
         # State Machine: BOOT -> LOADING -> LOGIN -> GAME
         self.state = "BOOT"
         self.loading_step = 0
         self.total_loading_steps = 6
         self.loading_msg = "Initializing..."
         self.loading_progress = 0.0
         
         # Core Pygame Setup
         pygame.init()
         self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
         pygame.display.set_caption("Soul of Wind")
         self.clock = pygame.time.Clock()
         self.running = True
         
-        # Assets containers (Loaded in LOADING state)
-        self.title_font = None
-        self.font = None
-        self.msg_font = None
-        self.bg_img = None
-        self.panel_img = None
-        self.btn_img = None
-        self.compass_img = None
-        self.light_surf = None
+        # Assets containers (Loaded in LOADING state)
+        self.title_font = None
+        self.font = None
+        self.msg_font = None
+        self.hud_font = None
+        self.bg_img = None
+        self.panel_img = None
+        self.btn_img = None
+        self.compass_img = None
+        self.light_surf = None
         self.firefly_surf = None
         self.char_assets = {}
         
         # Engine Systems (Initialized but not loaded)
         self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
         self.map_system = Map(SCREEN_WIDTH, SCREEN_HEIGHT) # Assets loaded later
         self.day_night = DayNightCycle(SCREEN_WIDTH, SCREEN_HEIGHT)
         self.input_manager = InputManager()
         
         # Game Data
-        self.player_pos = [400, 300]
-        self.player_speed = 5
-        self.other_players = {}
-        self.username = ""
-        self.connected = False
-        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
-        self.network_queue = queue.Queue() # Thread-safe queue
+        self.player_pos = [400.0, 300.0]
+        self.player_velocity = [0.0, 0.0]
+        self.player_max_speed = 240.0
+        self.player_accel = 10.0
+        self.player_friction = 6.0
+        self.player_sprint_multiplier = 1.6
+        self.player_stamina = 100.0
+        self.player_stamina_max = 100.0
+        self.player_stamina_regen = 22.0
+        self.player_stamina_drain = 35.0
+        self.player_health = 100.0
+        self.walk_phase = 0.0
+        self.other_players = {}
+        self.username = ""
+        self.connected = False
+        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
+        self.network_queue = queue.Queue() # Thread-safe queue
         self.status_msg = ""
         self.connecting = False
         
         # UI State
-        self.paused = False
-        self.show_controls = False
-        self.waiting_for_key = None
-        self.control_buttons = []
-        
-        # Switch to LOADING
-        self.state = "LOADING"
+        self.paused = False
+        self.show_controls = False
+        self.waiting_for_key = None
+        self.control_buttons = []
+        self.delta_time = 0.0
+        self.char_tint_cache = {}
+
+        self.ui_colors = {
+            "panel_bg": (20, 24, 35),
+            "panel_border": (70, 90, 120),
+            "accent": (120, 200, 160),
+            "accent_soft": (80, 150, 120),
+            "danger": (255, 120, 120),
+            "text": (235, 245, 255),
+            "muted": (170, 190, 210),
+        }
+
+        # Switch to LOADING
+        self.state = "LOADING"
 
     def update_loading(self):
         try:
-            if self.loading_step == 0:
-                self.loading_msg = "Loading Fonts & UI..."
-                self.title_font = pygame.font.Font(None, 74)
-                self.font = pygame.font.Font(None, 32)
-                self.msg_font = pygame.font.Font(None, 24)
-                
-                # Load UI Images
-                self.loading_bg = None
-                if os.path.exists("assets/loading_bg.png"):
-                    self.loading_bg = pygame.image.load("assets/loading_bg.png").convert()
+            if self.loading_step == 0:
+                self.loading_msg = "Loading Fonts & UI..."
+                self.title_font = pygame.font.Font(None, 74)
+                self.font = pygame.font.Font(None, 32)
+                self.msg_font = pygame.font.Font(None, 24)
+                self.hud_font = pygame.font.Font(None, 22)
+                
+                # Load UI Images
+                self.loading_bg = None
+                if os.path.exists("assets/loading_bg.png"):
+                    self.loading_bg = pygame.image.load("assets/loading_bg.png").convert()
                     self.loading_bg = pygame.transform.scale(self.loading_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
 
                 if os.path.exists("assets/bg.png"): self.bg_img = pygame.image.load("assets/bg.png").convert()
                 if os.path.exists("assets/panel.png"): self.panel_img = pygame.image.load("assets/panel.png").convert_alpha()
                 if os.path.exists("assets/button.png"): self.btn_img = pygame.image.load("assets/button.png").convert_alpha()
                 try:
                      self.compass_img = pygame.image.load("assets/ui/compass.png").convert_alpha() if os.path.exists("assets/ui/compass.png") else None
                 except: pass
                 
                 # Init UI Interactables (Buttons)
-                self.init_login_ui()
-                self.init_game_ui()
+                self.init_login_ui()
+                self.init_game_ui()
                 
             elif self.loading_step == 1:
                 self.loading_msg = "Generating Map Assets..."
                 self.map_system.load_assets()
                 
-            elif self.loading_step == 2:
-                self.loading_msg = "Loading Characters..."
-                self.load_sprites()
+            elif self.loading_step == 2:
+                self.loading_msg = "Loading Characters..."
+                self.load_sprites()
                 
             elif self.loading_step == 3:
                 self.loading_msg = "Pre-rendering Lighting Effects..."
                 self.light_surf = self.create_light_surf(128, (255, 255, 200))
                 self.firefly_surf = self.create_light_surf(16, (150, 255, 100))
                 # self.bloom_surf = pygame.Surface((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                 self.fireflies = [Firefly(random.randint(0, 1000), random.randint(0, 1000)) for _ in range(50)]
 
             elif self.loading_step == 4:
                 self.loading_msg = "Connecting to Server..."
                 # We don't connect yet, just setup
                 
             elif self.loading_step == 5:
                 self.loading_msg = "Done!"
                 time.sleep(0.5) # Fake delay for chillness
                 self.state = "LOGIN"
                 
-            self.loading_step += 1
-            self.loading_progress = min(1.0, self.loading_step / self.total_loading_steps)
-            
-        except Exception as e:
+            self.loading_step += 1
+            self.loading_progress = min(1.0, self.loading_step / self.total_loading_steps)
+            
+        except Exception as e:
             logging.error(f"Loading Error at step {self.loading_step}: {e}")
             traceback.print_exc()
             self.state = "LOGIN"
 
     def draw_loading(self):
         self.screen.fill((20, 20, 40))
         if hasattr(self, 'loading_bg') and self.loading_bg:
             self.screen.blit(self.loading_bg, (0, 0))
             
         # Draw Progress Bar
         bar_w = 400
         bar_h = 30
         x = SCREEN_WIDTH // 2 - bar_w // 2
         y = SCREEN_HEIGHT - 100
         
         # BG
         pygame.draw.rect(self.screen, (50, 50, 50), (x, y, bar_w, bar_h))
         # Fill
         fill_w = int(bar_w * self.loading_progress)
         pygame.draw.rect(self.screen, (100, 200, 100), (x, y, fill_w, bar_h))
         # Border
         pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_w, bar_h), 2)
         
         # Text
         if self.font:
@@ -178,117 +202,197 @@ class GameClient:
     def init_login_ui(self):
         # Login UI
         self.login_user_input = TextInput(300, 200, 200, 40, self.font, placeholder="Username")
         self.login_pass_input = TextInput(300, 260, 200, 40, self.font, placeholder="Password", is_password=True)
         self.btn_login = Button(300, 320, 95, 50, "Login", self.font, image=self.btn_img)
         self.btn_goto_register = Button(405, 320, 95, 50, "Register", self.font, bg_color=(100, 180, 100), image=self.btn_img)
         
         # Register UI
         self.reg_user_input = TextInput(300, 200, 200, 40, self.font, placeholder="New Username")
         self.reg_pass_input = TextInput(300, 260, 200, 40, self.font, placeholder="New Password", is_password=True)
         self.btn_register = Button(300, 320, 200, 50, "Create Account", self.font, image=self.btn_img)
         self.btn_back = Button(300, 380, 200, 40, "Back to Login", self.font, bg_color=(150, 150, 150), image=self.btn_img)
         
         # Character Creation UI
         self.btn_create_char = Button(300, 520, 200, 50, "Start Adventure", self.font, image=self.btn_img)
         self.temp_appearance = {"body": 0, "hair": 0, "shirt": 0, "pants": 0, "eyes": 0}
         self.my_appearance = None
         
     def init_game_ui(self):
         # Pause Menu UI
         self.btn_resume = Button(SCREEN_WIDTH//2 - 100, 200, 200, 50, "Resume", self.font, image=self.btn_img)
         self.btn_customize = Button(SCREEN_WIDTH//2 - 100, 270, 200, 50, "Customize", self.font, image=self.btn_img)
         self.btn_controls = Button(SCREEN_WIDTH//2 - 100, 340, 200, 50, "Controls", self.font, image=self.btn_img)
         self.btn_quit = Button(SCREEN_WIDTH//2 - 100, 480, 200, 50, "Quit", self.font, image=self.btn_img)
         
-    def load_sprites(self):
-        try:
-            self.char_assets = {}
-            # Helper to safely load
-            def load_safe(path):
-                if os.path.exists(path):
-                    return pygame.image.load(path).convert_alpha()
-                return None
+    def load_sprites(self):
+        try:
+            self.char_assets = {}
+            self.char_tint_cache = {}
+            # Helper to safely load
+            def load_safe(path):
+                if os.path.exists(path):
+                    return pygame.image.load(path).convert_alpha()
+                return None
 
             body_sheet = load_safe("assets/character/body.png")
             hair_sheet = load_safe("assets/character/hair.png")
             armor_sheet = load_safe("assets/character/armor.png")
             
             def get_frame(sheet):
                 if not sheet: return None
                 # If sheet is big enough, slice it. Else use whole.
                 if sheet.get_width() >= 64 and sheet.get_height() >= 128:
                     return sheet.subsurface((0, 0, 64, 128))
                 return sheet
 
-            self.char_assets['body'] = get_frame(body_sheet)
-            self.char_assets['hair'] = get_frame(hair_sheet)
-            self.char_assets['armor'] = get_frame(armor_sheet)
+            self.char_assets['body'] = get_frame(body_sheet)
+            self.char_assets['hair'] = get_frame(hair_sheet)
+            self.char_assets['armor'] = get_frame(armor_sheet)
             
         except Exception as e:
             logging.error(f"Failed to load char assets: {e}")
             self.char_assets = {}
 
-    def create_light_surf(self, radius, color):
-        # Create a radial gradient surface for lighting
+    def create_light_surf(self, radius, color):
+        # Create a radial gradient surface for lighting
         surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
         # Draw multiple concentric circles for gradient look
         for i in range(radius, 0, -2):
             alpha = int(255 * (1 - (i / radius))**2) # Quadratic falloff
             # Create a color with this alpha
             # Note: Putting alpha in the color tuple works for draw.circle with SRCALPHA surf
             c = (color[0], color[1], color[2], max(0, min(255, alpha * 0.5))) 
             pygame.draw.circle(surf, c, (radius, radius), i)
-        return surf
-
-    def draw_character(self, surface, x, y, appearance, zoom=1.0):
-        # appearance: {body: 0, hair: 0...} - Currently we only have 1 set of realistic assets
-        # In a full system, 'hair': 0 would map to hair_0.png, 'hair': 1 to hair_1.png
-        
-        base_w, base_h = 64, 128
-        dest_w = int(base_w * zoom)
-        dest_h = int(base_h * zoom)
-        
-        if not self.char_assets or not self.char_assets.get('body'):
-             # Fallback BLUE for missing assets
-             pygame.draw.rect(surface, (0, 0, 255), (x, y, 32 * zoom, 64 * zoom))
-             return
-
-        # Body
-        if 'body' in self.char_assets:
-            s = pygame.transform.scale(self.char_assets['body'], (dest_w, dest_h))
-            surface.blit(s, (x, y))
-            
-        # Shirt/Armor (If equipped in appearance)
-        if appearance.get('shirt', 1) == 1 and 'armor' in self.char_assets:
-            s = pygame.transform.scale(self.char_assets['armor'], (dest_w, dest_h))
-            surface.blit(s, (x, y))
-
-        # Hair
-        if appearance.get('hair', 1) == 1 and 'hair' in self.char_assets:
-            s = pygame.transform.scale(self.char_assets['hair'], (dest_w, dest_h))
-            surface.blit(s, (x, y))
+        return surf
+
+    def tint_surface(self, surface, color):
+        tinted = surface.copy()
+        tint = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
+        tint.fill(color)
+        tinted.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
+        return tinted
+
+    def get_tinted_asset(self, key, color):
+        cache_key = (key, color)
+        if cache_key in self.char_tint_cache:
+            return self.char_tint_cache[cache_key]
+        base = self.char_assets.get(key)
+        if not base:
+            return None
+        tinted = self.tint_surface(base, color)
+        self.char_tint_cache[cache_key] = tinted
+        return tinted
+
+    def draw_character(self, surface, x, y, appearance, zoom=1.0, bob=0.0):
+        # appearance: {body: 0, hair: 0...} - Currently we only have 1 set of realistic assets
+        # In a full system, 'hair': 0 would map to hair_0.png, 'hair': 1 to hair_1.png
+        appearance = appearance or {}
+        
+        base_w, base_h = 64, 128
+        dest_w = int(base_w * zoom)
+        dest_h = int(base_h * zoom)
+        y = y + bob
+
+        skin_tones = [(255, 219, 172), (235, 200, 150), (198, 134, 96), (141, 85, 36)]
+        hair_colors = [(42, 35, 30), (90, 70, 50), (25, 25, 25), (120, 40, 25), (180, 160, 120)]
+        shirt_colors = [(90, 140, 200), (120, 200, 160), (200, 120, 120), (150, 120, 200)]
+        pants_colors = [(50, 60, 90), (70, 70, 70), (90, 50, 50), (40, 80, 60)]
+        eye_colors = [(50, 80, 120), (80, 120, 80), (120, 90, 60), (60, 60, 60)]
+        skin_color = skin_tones[appearance.get('body', 0) % len(skin_tones)]
+        hair_color = hair_colors[appearance.get('hair', 0) % len(hair_colors)]
+        shirt_color = shirt_colors[appearance.get('shirt', 0) % len(shirt_colors)]
+        pants_color = pants_colors[appearance.get('pants', 0) % len(pants_colors)]
+        eye_color = eye_colors[appearance.get('eyes', 0) % len(eye_colors)]
+        
+        shadow_w = int(dest_w * 0.6)
+        shadow_h = int(dest_h * 0.2)
+        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
+        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
+        surface.blit(shadow, (x + dest_w * 0.2, y + dest_h - shadow_h + 6))
+        
+        if not self.char_assets or not self.char_assets.get('body'):
+             # Fallback BLUE for missing assets
+             pygame.draw.rect(surface, (60, 90, 160), (x, y, 32 * zoom, 64 * zoom))
+             pygame.draw.rect(surface, (20, 20, 20), (x, y + 32 * zoom, 32 * zoom, 16 * zoom))
+             return
+
+        # Body
+        if 'body' in self.char_assets:
+            body_asset = self.get_tinted_asset('body', skin_color) or self.char_assets['body']
+            s = pygame.transform.smoothscale(body_asset, (dest_w, dest_h))
+            surface.blit(s, (x, y))
+            
+        # Shirt/Armor (If equipped in appearance)
+        if appearance.get('shirt', 1) == 1 and 'armor' in self.char_assets:
+            armor_asset = self.get_tinted_asset('armor', shirt_color) or self.char_assets['armor']
+            s = pygame.transform.smoothscale(armor_asset, (dest_w, dest_h))
+            surface.blit(s, (x, y))
+
+        # Hair
+        if appearance.get('hair', 1) == 1 and 'hair' in self.char_assets:
+            hair_asset = self.get_tinted_asset('hair', hair_color) or self.char_assets['hair']
+            s = pygame.transform.smoothscale(hair_asset, (dest_w, dest_h))
+            surface.blit(s, (x, y))
+
+        # Pants overlay for extra variety
+        pants_rect = pygame.Rect(x + dest_w * 0.2, y + dest_h * 0.55, dest_w * 0.6, dest_h * 0.35)
+        pants_overlay = pygame.Surface((pants_rect.width, pants_rect.height), pygame.SRCALPHA)
+        pants_overlay.fill((*pants_color, 130))
+        surface.blit(pants_overlay, pants_rect.topleft)
+
+        # Eyes
+        eye_size = max(2, int(3 * zoom))
+        eye_y = y + int(dest_h * 0.28)
+        pygame.draw.circle(surface, eye_color, (int(x + dest_w * 0.42), eye_y), eye_size)
+        pygame.draw.circle(surface, eye_color, (int(x + dest_w * 0.58), eye_y), eye_size)
+
+    def draw_hud(self):
+        panel = pygame.Surface((280, 80), pygame.SRCALPHA)
+        panel.fill((*self.ui_colors["panel_bg"], 200))
+        pygame.draw.rect(panel, self.ui_colors["panel_border"], panel.get_rect(), 2, border_radius=8)
+        self.screen.blit(panel, (16, 16))
+
+        hp_ratio = max(0.0, min(1.0, self.player_health / 100.0))
+        st_ratio = max(0.0, min(1.0, self.player_stamina / self.player_stamina_max))
+        hp_w = int(200 * hp_ratio)
+        st_w = int(200 * st_ratio)
+
+        pygame.draw.rect(self.screen, (80, 20, 20), (32, 32, 200, 12), border_radius=6)
+        pygame.draw.rect(self.screen, (180, 60, 60), (32, 32, hp_w, 12), border_radius=6)
+        pygame.draw.rect(self.screen, (20, 60, 40), (32, 54, 200, 10), border_radius=6)
+        pygame.draw.rect(self.screen, (80, 180, 120), (32, 54, st_w, 10), border_radius=6)
+
+        info = f"X: {int(self.player_pos[0])}  Y: {int(self.player_pos[1])}"
+        info_surf = self.hud_font.render(info, True, self.ui_colors["muted"])
+        self.screen.blit(info_surf, (32, 70))
+
+    def draw_panel(self, rect):
+        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
+        panel.fill((*self.ui_colors["panel_bg"], 210))
+        pygame.draw.rect(panel, self.ui_colors["panel_border"], panel.get_rect(), 2, border_radius=12)
+        self.screen.blit(panel, rect.topleft)
 
     def connect_and_login(self, username, password, is_register=False):
         if self.connecting: return
         self.connecting = True
         self.status_msg = "Connecting..."
         
         def task():
             try:
                 # If not already connected, connect
                 if not self.connected:
                     self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                     self.client_socket.settimeout(5.0) # 5 sec timeout
                     self.client_socket.connect((SERVER_IP, SERVER_PORT))
                     self.client_socket.settimeout(None) # Reset blocking
                     self.connected = True
                     
                     # Start receiving thread
                     receive_thread = threading.Thread(target=self.receive_data)
                     receive_thread.daemon = True
                     receive_thread.start()
                 
                 # Send Packet
                 if is_register:
                     self.send_json({"type": "REGISTER", "username": username, "password": password})
                     self.status_msg = "Register request sent..."
@@ -362,151 +466,155 @@ class GameClient:
                     
                 elif msg_type == 'REGISTER_SUCCESS':
                     self.status_msg = "Registration Success! Please Login."
                     self.state = "LOGIN"
                     
                 elif msg_type == 'REGISTER_FAIL':
                     self.status_msg = msg.get('message', 'Registration Failed')
                 
                 elif msg_type == 'CREATE_CHAR_SUCCESS':
                     self.state = "GAME"
                     self.my_appearance = msg.get('appearance')
                     pygame.display.set_caption(f"Soul of Wind - Playing as {self.username}")
                     
             except queue.Empty:
                 break
 
     def send_json(self, data):
         if not self.connected:
             return # Fail silently or log error, but don't block
             
         try:
             self.client_socket.send(json.dumps(data).encode('utf-8'))
         except:
             self.connected = False
 
-    def handle_login_screen(self):
-        if self.bg_img:
-            self.screen.blit(self.bg_img, (0, 0))
-        else:
-            self.screen.fill((50, 50, 70))
-        
-        if self.panel_img:
-             # Center panel
-             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
-        
-        title_surf = self.title_font.render("Login", True, (200, 255, 200))
-        self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 100))
+    def handle_login_screen(self):
+        if self.bg_img:
+            self.screen.blit(self.bg_img, (0, 0))
+        else:
+            self.screen.fill((50, 50, 70))
+        
+        if self.panel_img:
+             # Center panel
+             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
+        else:
+            self.draw_panel(pygame.Rect(SCREEN_WIDTH//2 - 220, SCREEN_HEIGHT//2 - 190, 440, 360))
+        else:
+            self.draw_panel(pygame.Rect(SCREEN_WIDTH//2 - 220, SCREEN_HEIGHT//2 - 190, 440, 360))
+        
+        title_surf = self.title_font.render("Login", True, (200, 255, 200))
+        self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 100))
         
         self.login_user_input.draw(self.screen)
         self.login_pass_input.draw(self.screen)
         self.btn_login.draw(self.screen)
         self.btn_goto_register.draw(self.screen)
         
-        if self.status_msg:
-            msg_surf = self.msg_font.render(self.status_msg, True, (255, 100, 100))
-            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))
+        if self.status_msg:
+            msg_surf = self.msg_font.render(self.status_msg, True, (255, 100, 100))
+            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))
+
+        hint = self.msg_font.render("WASD to move, Shift to sprint, Scroll to zoom.", True, self.ui_colors["muted"])
+        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 480))
 
         if self.connecting:
             # Overlay to prevent interaction
             s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
             s.fill((0, 0, 0, 100))
             self.screen.blit(s, (0,0))
             spinner_text = self.font.render("Connecting...", True, (255, 255, 255))
             self.screen.blit(spinner_text, (SCREEN_WIDTH//2 - spinner_text.get_width()//2, SCREEN_HEIGHT//2))
             pygame.display.flip()
             
             # Allow quitting during connection attempt
             for event in pygame.event.get():
                 if event.type == pygame.QUIT:
                     self.running = False
             return
 
         for event in pygame.event.get():
             if event.type == pygame.QUIT: self.running = False
             
             self.login_user_input.handle_event(event)
             self.login_pass_input.handle_event(event)
             
             if self.btn_login.is_clicked(event):
                 u = self.login_user_input.get_text()
                 p = self.login_pass_input.get_text()
                 if u and p:
                     self.connect_and_login(u, p, is_register=False)
                 else:
                     self.status_msg = "Enter username/password"
                 
             if self.btn_goto_register.is_clicked(event):
                 self.state = "REGISTER"
                 self.status_msg = ""
             
             self.btn_login.check_hover(pygame.mouse.get_pos())
             self.btn_goto_register.check_hover(pygame.mouse.get_pos())
             
         pygame.display.flip()
 
     def handle_register_screen(self):
         if self.bg_img:
             self.screen.blit(self.bg_img, (0, 0))
         else:
             self.screen.fill((70, 50, 50))
 
-        if self.panel_img:
-             # Center panel
-             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
+        if self.panel_img:
+             # Center panel
+             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
+        else:
+            self.draw_panel(pygame.Rect(SCREEN_WIDTH//2 - 220, SCREEN_HEIGHT//2 - 190, 440, 360))
         
         title_surf = self.title_font.render("Register", True, (255, 200, 200))
         self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 100))
         
         self.reg_user_input.draw(self.screen)
         self.reg_pass_input.draw(self.screen)
         self.btn_register.draw(self.screen)
         self.btn_back.draw(self.screen)
         
-        if self.status_msg:
-            msg_surf = self.msg_font.render(self.status_msg, True, (255, 255, 100))
-            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))
-
-        if self.connecting:
-            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
-            s.fill((0, 0, 0, 100))
-            self.screen.blit(s, (0,0))
-            spinner_text = self.font.render("Connecting...", True, (255, 255, 255))
-            self.screen.blit(spinner_text, (SCREEN_WIDTH//2 - spinner_text.get_width()//2, SCREEN_HEIGHT//2))
-            pygame.display.flip()
-           # Event handling
-            for event in pygame.event.get():
-                if event.type == pygame.QUIT:
-                    self.running = False
-                if event.type == pygame.MOUSEBUTTONDOWN:
-                    if event.button == 4: # Scroll Up
-                        self.camera.set_zoom(self.camera.target_zoom + 0.1)
-                    elif event.button == 5: # Scroll Down
-                        self.camera.set_zoom(self.camera.target_zoom - 0.1)
-
-            pygame.display.flip()
-            return
+        if self.status_msg:
+            msg_surf = self.msg_font.render(self.status_msg, True, (255, 255, 100))
+            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))
+
+        hint = self.msg_font.render("WASD to move, Shift to sprint, Scroll to zoom.", True, self.ui_colors["muted"])
+        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 480))
+
+        if self.connecting:
+            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
+            s.fill((0, 0, 0, 100))
+            self.screen.blit(s, (0,0))
+            spinner_text = self.font.render("Connecting...", True, (255, 255, 255))
+            self.screen.blit(spinner_text, (SCREEN_WIDTH//2 - spinner_text.get_width()//2, SCREEN_HEIGHT//2))
+            pygame.display.flip()
+            for event in pygame.event.get():
+                if event.type == pygame.QUIT:
+                    self.running = False
+            return
 
         for event in pygame.event.get():
             if event.type == pygame.QUIT: self.running = False
             
             self.reg_user_input.handle_event(event)
             self.reg_pass_input.handle_event(event)
             
             if self.btn_register.is_clicked(event):
                 u = self.reg_user_input.get_text()
                 p = self.reg_pass_input.get_text()
                 if u and p:
                     self.connect_and_login(u, p, is_register=True)
                 else:
                     self.status_msg = "Please fill all fields."
                 
             if self.btn_back.is_clicked(event):
                 self.state = "LOGIN"
                 self.status_msg = ""
             
             self.btn_register.check_hover(pygame.mouse.get_pos())
             self.btn_back.check_hover(pygame.mouse.get_pos())
             
         pygame.display.flip()
 
     # Legacy sprites methods removed. Using new layered system defined above.
@@ -663,177 +771,217 @@ class GameClient:
             if self.btn_resume.is_clicked(event):
                 self.paused = False
             
             if self.btn_customize.is_clicked(event):
                 # Reuse the CREATE_CHARACTER logic but inside game
                 # For simplicity, just set state, but we need to know we are editing existing
                 self.state = "CREATE_CHARACTER" 
                 self.temp_appearance = self.my_appearance.copy()
             
             if self.btn_controls.is_clicked(event):
                 self.show_controls = True
                 
             if self.btn_quit.is_clicked(event):
                 self.running = False
                 
             if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                 self.paused = False
                 
             self.btn_resume.check_hover(pygame.mouse.get_pos())
             self.btn_customize.check_hover(pygame.mouse.get_pos())
             self.btn_controls.check_hover(pygame.mouse.get_pos())
             self.btn_quit.check_hover(pygame.mouse.get_pos())
         
         pygame.display.flip()
 
-    def handle_game(self):
-        # Input using InputManager
-        moved = False
-        
-        # Check Pause
-        for event in pygame.event.get():
-            if event.type == pygame.QUIT: self.running = False
-            if event.type == pygame.KEYDOWN:
-                if event.key == self.input_manager.bindings['PAUSE']:
-                    self.paused = True
-                    return
-
-        # Check Modifiers
-        keys = pygame.key.get_pressed()
-        is_sneaking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
-        current_speed = self.player_speed * 0.5 if is_sneaking else self.player_speed
-
-        if self.input_manager.is_pressed('MOVE_UP'): 
-            self.player_pos[1] -= current_speed
-            moved = True
-        if self.input_manager.is_pressed('MOVE_DOWN'): 
-            self.player_pos[1] += current_speed
-            moved = True
-        if self.input_manager.is_pressed('MOVE_LEFT'): 
-            self.player_pos[0] -= current_speed
-            moved = True
-        if self.input_manager.is_pressed('MOVE_RIGHT'): 
-            self.player_pos[0] += current_speed
-            moved = True
-            
-        if self.input_manager.is_pressed('PAUSE'): # Escape
-            self.paused = True
-            
-        if moved and self.connected:
-             self.send_json({"type": "MOVE", "pos": {"x": self.player_pos[0], "y": self.player_pos[1]}})
-
-        # Update Systems
-        self.camera.update(self.player_pos)
+    def handle_game(self):
+        # Input using InputManager
+        moved = False
+        dt = max(self.delta_time, 1 / 120)
+        
+        # Check Pause
+        for event in pygame.event.get():
+            if event.type == pygame.QUIT: self.running = False
+            if event.type == pygame.KEYDOWN:
+                if event.key == self.input_manager.bindings['PAUSE']:
+                    self.paused = True
+                    return
+            if event.type == pygame.MOUSEWHEEL:
+                self.camera.set_zoom(self.camera.target_zoom + event.y * 0.1)
+
+        # Check Modifiers
+        keys = pygame.key.get_pressed()
+        is_sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
+
+        move_x = 0
+        move_y = 0
+        if self.input_manager.is_pressed('MOVE_UP'):
+            move_y -= 1
+        if self.input_manager.is_pressed('MOVE_DOWN'):
+            move_y += 1
+        if self.input_manager.is_pressed('MOVE_LEFT'):
+            move_x -= 1
+        if self.input_manager.is_pressed('MOVE_RIGHT'):
+            move_x += 1
+
+        if move_x != 0 or move_y != 0:
+            norm = math.hypot(move_x, move_y) or 1
+            move_x /= norm
+            move_y /= norm
+            moved = True
+
+        sprint_ready = is_sprinting and self.player_stamina > 5
+        speed = self.player_max_speed * (self.player_sprint_multiplier if sprint_ready else 1.0)
+        target_vx = move_x * speed
+        target_vy = move_y * speed
+
+        blend = min(1.0, self.player_accel * dt)
+        self.player_velocity[0] += (target_vx - self.player_velocity[0]) * blend
+        self.player_velocity[1] += (target_vy - self.player_velocity[1]) * blend
+
+        if not moved:
+            damp = max(0.0, 1.0 - self.player_friction * dt)
+            self.player_velocity[0] *= damp
+            self.player_velocity[1] *= damp
+
+        self.player_pos[0] += self.player_velocity[0] * dt
+        self.player_pos[1] += self.player_velocity[1] * dt
+            
+        if self.input_manager.is_pressed('PAUSE'): # Escape
+            self.paused = True
+            
+        if moved and self.connected:
+             self.send_json({"type": "MOVE", "pos": {"x": self.player_pos[0], "y": self.player_pos[1]}})
+
+        if sprint_ready and moved:
+            self.player_stamina = max(0.0, self.player_stamina - self.player_stamina_drain * dt)
+        else:
+            self.player_stamina = min(self.player_stamina_max, self.player_stamina + self.player_stamina_regen * dt)
+
+        # Update Systems
+        self.camera.update(self.player_pos)
         
         # Day Night Step (DISABLED FOR STABILITY)
         dt = 1/60 * 5 
         # self.day_night.update(dt)
 
         # Draw World Layer 1: Ground
         self.screen.fill(BG_COLOR)
         self.map_system.draw(self.screen, self.camera)
         
         # Collect Renderables for Y-Sort (Players, Vegetation, Animals)
         renderables = []
         
         # 1. Self
         renderables.append({
             'type': 'player',
             'y': self.player_pos[1],
             'x': self.player_pos[0],
             'data': {'app': self.my_appearance, 'name': self.username}
         })
         
         # 2. Others
         for pid, pdata in self.other_players.items():
             if pdata.get('pos'):
                 renderables.append({
                     'type': 'player',
                     'y': pdata['pos']['y'],
                     'x': pdata['pos']['x'],
                     'data': {'app': pdata.get('appearance'), 'name': pdata.get('username')}
                 })
         
         # 3. Vegetation
         visible_veg = self.map_system.get_visible_vegetation(self.camera)
         for veg in visible_veg:
             renderables.append({
                 'type': 'vegetation',
                 'y': veg.y,
                 'x': veg.x,
                 'data': veg
             })
             
         # Sort by Y
         renderables.sort(key=lambda r: r['y'])
         
-        # Draw Loop
-        zoom = self.camera.zoom_level
-        
-        for r in renderables:
-            sx, sy = self.camera.apply_pos(r['x'], r['y'])
+        # Draw Loop
+        zoom = self.camera.zoom_level
+        speed_mag = math.hypot(self.player_velocity[0], self.player_velocity[1])
+        if speed_mag > 2:
+            self.walk_phase += dt * (6 + speed_mag * 0.02)
+        else:
+            self.walk_phase *= max(0.0, 1.0 - 6 * dt)
+        
+        for r in renderables:
+            sx, sy = self.camera.apply_pos(r['x'], r['y'])
             
             # Culling
-            if -128 < sx < SCREEN_WIDTH and -128 < sy < SCREEN_HEIGHT:
-                if r['type'] == 'player':
-                    self.draw_character(self.screen, sx, sy, r['data']['app'], zoom)
-                    # Name
-                    name_surf = self.msg_font.render(r['data']['name'], True, (255, 255, 255))
-                    self.screen.blit(name_surf, (sx, sy - 20))
+            if -128 < sx < SCREEN_WIDTH and -128 < sy < SCREEN_HEIGHT:
+                if r['type'] == 'player':
+                    bob = math.sin(self.walk_phase) * 2 * zoom if r['data']['name'] == self.username else 0.0
+                    self.draw_character(self.screen, sx, sy, r['data']['app'], zoom, bob=bob)
+                    # Name
+                    name_surf = self.msg_font.render(r['data']['name'], True, (255, 255, 255))
+                    self.screen.blit(name_surf, (sx, sy - 20))
                     
-                elif r['type'] == 'vegetation':
-                    veg = r['data']
-                    asset = self.map_system.assets.get(veg.type)
-                    if asset:
-                        # Simple draw without sway for now to test stability
-                        # Scale
-                        w = int(asset.get_width() * zoom)
-                        h = int(asset.get_height() * zoom)
-                        scaled = pygame.transform.scale(asset, (w, h))
-                        self.screen.blit(scaled, (sx, sy - h + 32*zoom))
+                elif r['type'] == 'vegetation':
+                    veg = r['data']
+                    asset = self.map_system.assets.get(veg.type)
+                    if asset:
+                        # Simple draw without sway for now to test stability
+                        # Scale
+                        if isinstance(asset, pygame.Surface):
+                            w = int(asset.get_width() * zoom)
+                            h = int(asset.get_height() * zoom)
+                            scaled = self.map_system.get_scaled_surface(veg.type, (w, h))
+                            self.screen.blit(scaled, (sx, sy - h + 32 * zoom))
+                        else:
+                            pygame.draw.circle(self.screen, asset, (sx + 8, sy + 8), max(2, int(6 * zoom)))
 
         # --- VISUAL FX DISABLED ---
         # No Darkness, No Lights, No Fireflies for now.
         
         # UI
-        if self.compass_img:
-            comp_s = pygame.transform.scale(self.compass_img, (64, 64))
-            self.screen.blit(comp_s, (SCREEN_WIDTH - 80, 20))
-
-        # Connection status
-        if not self.connected:
-            text = self.font.render("Lost Connection!", True, (255, 100, 100))
-            self.screen.blit(text, (10, 10))
+        if self.compass_img:
+            comp_s = pygame.transform.scale(self.compass_img, (64, 64))
+            self.screen.blit(comp_s, (SCREEN_WIDTH - 80, 20))
+
+        self.draw_hud()
+
+        # Connection status
+        if not self.connected:
+            text = self.font.render("Lost Connection!", True, (255, 100, 100))
+            self.screen.blit(text, (10, 10))
 
         pygame.display.flip()
 
-    def run(self):
-        logging.info("Entering main loop...")
-        while self.running:
-            self.clock.tick(FPS)
-            
-            if self.state == "LOADING":
+    def run(self):
+        logging.info("Entering main loop...")
+        while self.running:
+            dt_ms = self.clock.tick(FPS)
+            self.delta_time = dt_ms / 1000.0
+            
+            if self.state == "LOADING":
                 self.update_loading()
                 self.draw_loading()
                 # Pump events
                 for event in pygame.event.get():
                     if event.type == pygame.QUIT:
                         self.running = False
             
             elif self.state == "LOGIN":
                 self.process_network_messages()
                 self.handle_login_screen()
                 
             elif self.state == "REGISTER":
                 self.process_network_messages()
                 self.handle_register_screen()
                 
             elif self.state == "CREATE_CHARACTER":
                 self.process_network_messages()
                 self.handle_create_character_screen()
                 
             elif self.state == "GAME":
                 self.process_network_messages()
                 if self.paused:
                     if self.show_controls:
                         self.handle_controls_screen()
                     else:
 
EOF
)
