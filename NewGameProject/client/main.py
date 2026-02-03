import pygame
import sys
import socket
import threading
import json
import logging
import traceback
import queue
from ui import Button, TextInput
from game_engine import Camera, Map, InputManager, TILE_SIZE, DayNightCycle, Firefly
import random
import time
import math
import os

# ... imports assumed correct at top

# Setup logging
logging.basicConfig(
    filename='client_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Also log to stdout
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)

logging.info("Starting game client...")

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
        
        # Assets containers (Loaded in LOADING state)
        self.title_font = None
        self.font = None
        self.msg_font = None
        self.bg_img = None
        self.panel_img = None
        self.btn_img = None
        self.compass_img = None
        self.light_surf = None
        self.firefly_surf = None
        self.char_assets = {}
        
        # Engine Systems (Initialized but not loaded)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.map_system = Map(SCREEN_WIDTH, SCREEN_HEIGHT) # Assets loaded later
        self.day_night = DayNightCycle(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.input_manager = InputManager()
        
        # Game Data
        self.player_pos = [400, 300]
        self.player_speed = 5
        self.other_players = {}
        self.username = ""
        self.connected = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.network_queue = queue.Queue() # Thread-safe queue
        self.status_msg = ""
        self.connecting = False
        
        # UI State
        self.paused = False
        self.show_controls = False
        self.waiting_for_key = None
        self.control_buttons = []
        
        # Switch to LOADING
        self.state = "LOADING"

    def update_loading(self):
        try:
            if self.loading_step == 0:
                self.loading_msg = "Loading Fonts & UI..."
                self.title_font = pygame.font.Font(None, 74)
                self.font = pygame.font.Font(None, 32)
                self.msg_font = pygame.font.Font(None, 24)
                
                # Load UI Images
                self.loading_bg = None
                if os.path.exists("assets/loading_bg.png"):
                    self.loading_bg = pygame.image.load("assets/loading_bg.png").convert()
                    self.loading_bg = pygame.transform.scale(self.loading_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

                if os.path.exists("assets/bg.png"): self.bg_img = pygame.image.load("assets/bg.png").convert()
                if os.path.exists("assets/panel.png"): self.panel_img = pygame.image.load("assets/panel.png").convert_alpha()
                if os.path.exists("assets/button.png"): self.btn_img = pygame.image.load("assets/button.png").convert_alpha()
                try:
                     self.compass_img = pygame.image.load("assets/ui/compass.png").convert_alpha() if os.path.exists("assets/ui/compass.png") else None
                except: pass
                
                # Init UI Interactables (Buttons)
                self.init_login_ui()
                self.init_game_ui()
                
            elif self.loading_step == 1:
                self.loading_msg = "Generating Map Assets..."
                self.map_system.load_assets()
                
            elif self.loading_step == 2:
                self.loading_msg = "Loading Characters..."
                self.load_sprites()
                
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
                
            self.loading_step += 1
            self.loading_progress = min(1.0, self.loading_step / self.total_loading_steps)
            
        except Exception as e:
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
            txt = self.font.render(self.loading_msg, True, (255, 255, 255))
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, y - 40))
            
        pygame.display.flip()

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
        
    def load_sprites(self):
        try:
            self.char_assets = {}
            # Helper to safely load
            def load_safe(path):
                if os.path.exists(path):
                    return pygame.image.load(path).convert_alpha()
                return None

            body_sheet = load_safe("assets/character/body.png")
            hair_sheet = load_safe("assets/character/hair.png")
            armor_sheet = load_safe("assets/character/armor.png")
            
            def get_frame(sheet):
                if not sheet: return None
                # If sheet is big enough, slice it. Else use whole.
                if sheet.get_width() >= 64 and sheet.get_height() >= 128:
                    return sheet.subsurface((0, 0, 64, 128))
                return sheet

            self.char_assets['body'] = get_frame(body_sheet)
            self.char_assets['hair'] = get_frame(hair_sheet)
            self.char_assets['armor'] = get_frame(armor_sheet)
            
        except Exception as e:
            logging.error(f"Failed to load char assets: {e}")
            self.char_assets = {}

    def create_light_surf(self, radius, color):
        # Create a radial gradient surface for lighting
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        # Draw multiple concentric circles for gradient look
        for i in range(radius, 0, -2):
            alpha = int(255 * (1 - (i / radius))**2) # Quadratic falloff
            # Create a color with this alpha
            # Note: Putting alpha in the color tuple works for draw.circle with SRCALPHA surf
            c = (color[0], color[1], color[2], max(0, min(255, alpha * 0.5))) 
            pygame.draw.circle(surf, c, (radius, radius), i)
        return surf

    def draw_character(self, surface, x, y, appearance, zoom=1.0):
        # appearance: {body: 0, hair: 0...} - Currently we only have 1 set of realistic assets
        # In a full system, 'hair': 0 would map to hair_0.png, 'hair': 1 to hair_1.png
        
        base_w, base_h = 64, 128
        dest_w = int(base_w * zoom)
        dest_h = int(base_h * zoom)
        
        if not self.char_assets or not self.char_assets.get('body'):
             # Fallback BLUE for missing assets
             pygame.draw.rect(surface, (0, 0, 255), (x, y, 32 * zoom, 64 * zoom))
             return

        # Body
        if 'body' in self.char_assets:
            s = pygame.transform.scale(self.char_assets['body'], (dest_w, dest_h))
            surface.blit(s, (x, y))
            
        # Shirt/Armor (If equipped in appearance)
        if appearance.get('shirt', 1) == 1 and 'armor' in self.char_assets:
            s = pygame.transform.scale(self.char_assets['armor'], (dest_w, dest_h))
            surface.blit(s, (x, y))

        # Hair
        if appearance.get('hair', 1) == 1 and 'hair' in self.char_assets:
            s = pygame.transform.scale(self.char_assets['hair'], (dest_w, dest_h))
            surface.blit(s, (x, y))

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
                else:
                    self.send_json({"type": "LOGIN", "username": username, "password": password})
                    self.status_msg = "Logging in..."
                    
            except Exception as e:
                logging.error(f"Connection failed: {e}")
                self.status_msg = "Connection Failed!"
                self.connected = False
            finally:
                self.connecting = False

        threading.Thread(target=task).start()

    def receive_data(self):
        while self.running and self.connected:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    self.network_queue.put({"type": "DISCONNECT"})
                    self.connected = False
                    break
                try:
                    # Basic JSON split to handle concatenated packets
                    try:
                         msg = json.loads(data)
                         self.network_queue.put(msg)
                    except json.JSONDecodeError:
                        fixed_data = data.replace('}{', '}|{')
                        parts = fixed_data.split('|')
                        for part in parts:
                            try:
                                msg = json.loads(part)
                                self.network_queue.put(msg)
                            except:
                                pass
                except Exception:
                    pass
            except Exception as e:
                logging.error(f"Error receiving data: {e}")
                self.connected = False
                break

    def process_network_messages(self):
        while not self.network_queue.empty():
            try:
                msg = self.network_queue.get_nowait()
                msg_type = msg.get('type')
                
                if msg_type == 'DISCONNECT':
                    self.status_msg = "Lost connection to server."
                    self.connected = False

                elif msg_type == 'GAME_STATE':
                    self.other_players = msg.get('data', {})
                    
                elif msg_type == 'LOGIN_SUCCESS':
                    self.username = msg.get('username')
                    if msg.get('has_character'):
                        self.state = "GAME"
                        self.my_appearance = msg.get('appearance')
                        pygame.display.set_caption(f"Soul of Wind - Playing as {self.username}")
                    else:
                        self.state = "CREATE_CHARACTER"
                        pygame.display.set_caption(f"Soul of Wind - Create Character")
                    
                elif msg_type == 'LOGIN_FAIL':
                    self.status_msg = msg.get('message', 'Login Failed')
                    
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

    def handle_login_screen(self):
        if self.bg_img:
            self.screen.blit(self.bg_img, (0, 0))
        else:
            self.screen.fill((50, 50, 70))
        
        if self.panel_img:
             # Center panel
             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
        
        title_surf = self.title_font.render("Login", True, (200, 255, 200))
        self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 100))
        
        self.login_user_input.draw(self.screen)
        self.login_pass_input.draw(self.screen)
        self.btn_login.draw(self.screen)
        self.btn_goto_register.draw(self.screen)
        
        if self.status_msg:
            msg_surf = self.msg_font.render(self.status_msg, True, (255, 100, 100))
            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))

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

        if self.panel_img:
             # Center panel
             self.screen.blit(self.panel_img, (SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 175))
        
        title_surf = self.title_font.render("Register", True, (255, 200, 200))
        self.screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 100))
        
        self.reg_user_input.draw(self.screen)
        self.reg_pass_input.draw(self.screen)
        self.btn_register.draw(self.screen)
        self.btn_back.draw(self.screen)
        
        if self.status_msg:
            msg_surf = self.msg_font.render(self.status_msg, True, (255, 255, 100))
            self.screen.blit(msg_surf, (SCREEN_WIDTH//2 - msg_surf.get_width()//2, 450))

        if self.connecting:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 100))
            self.screen.blit(s, (0,0))
            spinner_text = self.font.render("Connecting...", True, (255, 255, 255))
            self.screen.blit(spinner_text, (SCREEN_WIDTH//2 - spinner_text.get_width()//2, SCREEN_HEIGHT//2))
            pygame.display.flip()
           # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4: # Scroll Up
                        self.camera.set_zoom(self.camera.target_zoom + 0.1)
                    elif event.button == 5: # Scroll Down
                        self.camera.set_zoom(self.camera.target_zoom - 0.1)

            pygame.display.flip()
            return

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

    def handle_create_character_screen(self):
        if self.bg_img:
            self.screen.blit(self.bg_img, (0, 0))
        else:
            self.screen.fill((30, 30, 40))

        # Semi-transparent backing for char creation
        s = pygame.Surface((600, 500), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        self.screen.blit(s, (100, 50))
        
        # Title
        title = self.title_font.render("Create Character", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Preview
        pv_x, pv_y = SCREEN_WIDTH // 2 - 32, 150
        # Draw background for preview
        pygame.draw.rect(self.screen, (60, 60, 80), (pv_x - 20, pv_y - 20, 104, 104))
        self.draw_character(self.screen, pv_x, pv_y, self.temp_appearance)
        
        # Controls
        categories = ["body", "hair", "shirt", "pants", "eyes"]
        limits = [5, 10, 10, 10, 10]
        y_start = 300
        
        for idx, cat in enumerate(categories):
            # Label
            lbl = self.font.render(cat.capitalize(), True, (200, 200, 200))
            self.screen.blit(lbl, (200, y_start + idx * 40))
            
            # Left Button (<)
            l_btn = Button(350, y_start + idx * 40, 30, 30, "<", self.font)
            l_btn.draw(self.screen)
            
            # Val
            val = self.temp_appearance[cat]
            val_surf = self.font.render(str(val + 1), True, (255, 255, 255))
            self.screen.blit(val_surf, (400, y_start + idx * 40))
            
            # Right Button (>)
            r_btn = Button(450, y_start + idx * 40, 30, 30, ">", self.font)
            r_btn.draw(self.screen)
            
            # Interactions - Hacky inline handling for now
            if pygame.mouse.get_pressed()[0]:
                m_pos = pygame.mouse.get_pos()
                # Debounce needed or simple check
                pass 
                # Actually, stick to event loop logic properly below
        
        # Create Button
        self.btn_create_char.draw(self.screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            
            # ... (Mouse handling logic kept simplified for brevity)
            m_pos = pygame.mouse.get_pos()
            if event.type == pygame.MOUSEBUTTONDOWN:
                 for idx, cat in enumerate(categories):
                    # Left
                    if 350 <= m_pos[0] <= 380 and (y_start + idx * 40) <= m_pos[1] <= (y_start + idx * 40 + 30):
                         self.temp_appearance[cat] = (self.temp_appearance[cat] - 1) % limits[idx]
                    # Right
                    elif 450 <= m_pos[0] <= 480 and (y_start + idx * 40) <= m_pos[1] <= (y_start + idx * 40 + 30):
                         self.temp_appearance[cat] = (self.temp_appearance[cat] + 1) % limits[idx]
            
            if self.btn_create_char.is_clicked(event):
                self.send_json({"type": "CREATE_CHARACTER", "appearance": self.temp_appearance})
                self.status_msg = "Saving..."
                # If we are logged in, we stay connected, server sends SUCCESS, state -> GAME
                
            self.btn_create_char.check_hover(m_pos)
            
        pygame.display.flip()

    def handle_controls_screen(self):
        # Overlay
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        self.screen.blit(s, (0,0))
        
        title = self.title_font.render("Controls", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        y = 150
        for action, key_code in self.input_manager.bindings.items():
            txt_surf = self.font.render(f"{action}:", True, (200, 200, 200))
            self.screen.blit(txt_surf, (200, y))
            
            key_name = pygame.key.name(key_code)
            if self.waiting_for_key == action:
                key_name = "Apply Key..."
                color = (255, 255, 0)
            else:
                color = (255, 255, 255)
            
            # Simple clickable text area for now
            val_surf = self.font.render(key_name, True, color)
            val_rect = val_surf.get_rect(topleft=(400, y))
            self.screen.blit(val_surf, val_rect)
            
            # Check click
            if pygame.mouse.get_pressed()[0]:
                m_pos = pygame.mouse.get_pos()
                if val_rect.collidepoint(m_pos):
                     self.waiting_for_key = action
            
            y += 40

        # Back Button
        back_btn = Button(50, 50, 100, 40, "Back", self.font, image=self.btn_img)
        back_btn.draw(self.screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            
            if self.waiting_for_key:
                if event.type == pygame.KEYDOWN:
                    if event.key != pygame.K_ESCAPE:
                        self.input_manager.bindings[self.waiting_for_key] = event.key
                        self.input_manager.save()
                    self.waiting_for_key = None
            else:
                if back_btn.is_clicked(event):
                    self.show_controls = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_controls = False

        pygame.display.flip()

    def handle_pause_menu(self):
        # Draw transparent overlay
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        self.screen.blit(s, (0,0))
        
        title = self.title_font.render("Paused", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        self.btn_resume.draw(self.screen)
        self.btn_customize.draw(self.screen)
        self.btn_controls.draw(self.screen)
        self.btn_quit.draw(self.screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            
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

    def handle_game(self):
        # Input using InputManager
        moved = False
        
        # Check Pause
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == self.input_manager.bindings['PAUSE']:
                    self.paused = True
                    return

        # Check Modifiers
        keys = pygame.key.get_pressed()
        is_sneaking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        current_speed = self.player_speed * 0.5 if is_sneaking else self.player_speed

        if self.input_manager.is_pressed('MOVE_UP'): 
            self.player_pos[1] -= current_speed
            moved = True
        if self.input_manager.is_pressed('MOVE_DOWN'): 
            self.player_pos[1] += current_speed
            moved = True
        if self.input_manager.is_pressed('MOVE_LEFT'): 
            self.player_pos[0] -= current_speed
            moved = True
        if self.input_manager.is_pressed('MOVE_RIGHT'): 
            self.player_pos[0] += current_speed
            moved = True
            
        if self.input_manager.is_pressed('PAUSE'): # Escape
            self.paused = True
            
        if moved and self.connected:
             self.send_json({"type": "MOVE", "pos": {"x": self.player_pos[0], "y": self.player_pos[1]}})

        # Update Systems
        self.camera.update(self.player_pos)
        
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
        
        # Draw Loop
        zoom = self.camera.zoom_level
        
        for r in renderables:
            sx, sy = self.camera.apply_pos(r['x'], r['y'])
            
            # Culling
            if -128 < sx < SCREEN_WIDTH and -128 < sy < SCREEN_HEIGHT:
                if r['type'] == 'player':
                    self.draw_character(self.screen, sx, sy, r['data']['app'], zoom)
                    # Name
                    name_surf = self.msg_font.render(r['data']['name'], True, (255, 255, 255))
                    self.screen.blit(name_surf, (sx, sy - 20))
                    
                elif r['type'] == 'vegetation':
                    veg = r['data']
                    asset = self.map_system.assets.get(veg.type)
                    if asset:
                        # Simple draw without sway for now to test stability
                        # Scale
                        w = int(asset.get_width() * zoom)
                        h = int(asset.get_height() * zoom)
                        scaled = pygame.transform.scale(asset, (w, h))
                        self.screen.blit(scaled, (sx, sy - h + 32*zoom))

        # --- VISUAL FX DISABLED ---
        # No Darkness, No Lights, No Fireflies for now.
        
        # UI
        if self.compass_img:
            comp_s = pygame.transform.scale(self.compass_img, (64, 64))
            self.screen.blit(comp_s, (SCREEN_WIDTH - 80, 20))

        # Connection status
        if not self.connected:
            text = self.font.render("Lost Connection!", True, (255, 100, 100))
            self.screen.blit(text, (10, 10))

        pygame.display.flip()

    def run(self):
        logging.info("Entering main loop...")
        while self.running:
            self.clock.tick(FPS)
            
            if self.state == "LOADING":
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
                        self.handle_pause_menu()
                else:
                    self.handle_game()
            
        logging.info("Quitting pygame...")
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        game = GameClient()
        game.run()
    except Exception as e:
        logging.critical("CRASH DETECTED!", exc_info=True)
        print("CRASH DETECTED! Check client_debug.log")
        input("Press Enter to exit...")
