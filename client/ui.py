 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/client/ui.py b/client/ui.py
index 435d32d3c7d3a18ab44564b33bb6a96c1ea9892c..97e05a98750d77077452b95f889498441b76776a 100644
--- a/client/ui.py
+++ b/client/ui.py
@@ -1,106 +1,110 @@
 import pygame
 
 class Button:
     def __init__(self, x, y, width, height, text, font, bg_color=(100, 100, 255), text_color=(255, 255, 255), hover_color=(150, 150, 255), image=None):
         self.rect = pygame.Rect(x, y, width, height)
         self.text = text
         self.font = font
         self.bg_color = bg_color
         self.text_color = text_color
         self.hover_color = hover_color
         self.is_hovered = False
         self.image = image
         if self.image:
             self.image = pygame.transform.scale(self.image, (width, height))
 
     def check_hover(self, mouse_pos):
         self.is_hovered = self.rect.collidepoint(mouse_pos)
 
     def is_clicked(self, event):
         if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if self.is_hovered:
                 return True
         return False
 
-    def draw(self, screen):
-        if self.image:
-             # Basic tint or brightness increase on hover could be added, but keeping it simple
-             screen.blit(self.image, self.rect)
-             if self.is_hovered:
-                 # Add a subtle highlight overlay
-                 s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
-                 s.fill((255, 255, 255, 50))
-                 screen.blit(s, self.rect)
-        else:
-            color = self.hover_color if self.is_hovered else self.bg_color
-            pygame.draw.rect(screen, color, self.rect, border_radius=5)
-        
-        text_surf = self.font.render(self.text, True, self.text_color)
-        text_rect = text_surf.get_rect(center=self.rect.center)
-        screen.blit(text_surf, text_rect)
+    def draw(self, screen):
+        if self.image:
+             # Basic tint or brightness increase on hover could be added, but keeping it simple
+             screen.blit(self.image, self.rect)
+             if self.is_hovered:
+                 # Add a subtle highlight overlay
+                 s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
+                 s.fill((255, 255, 255, 50))
+                 screen.blit(s, self.rect)
+        else:
+            shadow_rect = self.rect.move(0, 3)
+            pygame.draw.rect(screen, (0, 0, 0, 120), shadow_rect, border_radius=6)
+            color = self.hover_color if self.is_hovered else self.bg_color
+            pygame.draw.rect(screen, color, self.rect, border_radius=6)
+        
+        text_surf = self.font.render(self.text, True, self.text_color)
+        text_rect = text_surf.get_rect(center=self.rect.center)
+        screen.blit(text_surf, text_rect)
 
 class TextInput:
     def __init__(self, x, y, width, height, font, placeholder="Type here...", bg_color=(255, 255, 255), text_color=(0, 0, 0), is_password=False):
         self.rect = pygame.Rect(x, y, width, height)
         self.font = font
         self.text = ""
         self.placeholder = placeholder
         self.bg_color = bg_color
         self.text_color = text_color
         self.is_password = is_password
         self.active = False
         self.border_color_active = (0, 200, 255)
         self.border_color_inactive = (200, 200, 200)
 
     def handle_event(self, event):
         if event.type == pygame.MOUSEBUTTONDOWN:
             if self.rect.collidepoint(event.pos):
                 self.active = True
             else:
                 self.active = False
             return self.active
         
         if self.active and event.type == pygame.KEYDOWN:
             if event.key == pygame.K_RETURN:
                 return True
             elif event.key == pygame.K_BACKSPACE:
                 self.text = self.text[:-1]
             elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                 try:
                     self.text += pygame.scrap.get(pygame.SCRAP_TEXT).decode('utf-8').strip('\x00')
                 except:
                     pass
             else:
                 self.text += event.unicode
             return True
                 
         return False
 
-    def draw(self, screen):
-        # Draw background
-        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)
+    def draw(self, screen):
+        # Draw background
+        shadow_rect = self.rect.inflate(4, 4).move(0, 2)
+        pygame.draw.rect(screen, (0, 0, 0, 120), shadow_rect, border_radius=6)
+        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)
         
         # Draw border
         if self.active:
             border_color = self.border_color_active
             thickness = 3
         else:
             border_color = self.border_color_inactive
             thickness = 2
             
         pygame.draw.rect(screen, border_color, self.rect, thickness, border_radius=5)
         
         # Render text
         if self.text:
             if self.is_password:
                 display_text = "*" * len(self.text)
             else:
                 display_text = self.text
             color = self.text_color
         else:
             display_text = self.placeholder
             color = (150, 150, 150)
         
         text_surf = self.font.render(display_text, True, color)
         
         # Vertical center
 
EOF
)
