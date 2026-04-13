import pygame
import sys
import math
import random
from pygame.locals import *

# Initialize Pygame
pygame.init()

# Set up the window (now resizable)
WIDTH, HEIGHT = 1000, 700  # Adjusted to match the animation code for better space
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Login Window with Background Animation")

# Colors for login form
WHITE = (255, 255, 255)
PINK = (255, 51, 153)
DARK_GRAY = (29, 29, 29)
GRAY = (128, 128, 128)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
TRANSPARENT_BLACK = (0, 0, 0, 128)  # For overlay

# Colors for background animation
BG_COLOR = (10, 14, 39)
SHAPE_COLORS = [(42, 77, 109), (61, 90, 122), (74, 107, 138), (90, 122, 154), (106, 138, 170), (58, 111, 138)]

# Fonts
try:
    login_font = pygame.font.SysFont("Impact", 40)
    welcome_font = pygame.font.SysFont("goudyoldstyle", 22)
    label_font = pygame.font.SysFont("goudyoldstyle", 22)
    input_font = pygame.font.SysFont("goudyoldstyle", 18)
    button_font = pygame.font.SysFont("sans serif", 27, bold=True)  # Bold for Login
    feedback_font = pygame.font.SysFont("goudyoldstyle", 18)
    link_font = pygame.font.SysFont("goudyoldstyle", 18)
    popup_font = pygame.font.SysFont("goudyoldstyle", 22)
    ok_button_font = pygame.font.SysFont("goudyoldstyle", 18)
except:
    # Fallback if fonts not available
    login_font = pygame.font.SysFont(None, 48)
    welcome_font = pygame.font.SysFont(None, 36)
    label_font = pygame.font.SysFont(None, 24)
    input_font = pygame.font.SysFont(None, 20)
    button_font = pygame.font.SysFont(None, 27, bold=True)  # Bold for Login
    feedback_font = pygame.font.SysFont(None, 18)
    link_font = pygame.font.SysFont(None, 18)
    popup_font = pygame.font.SysFont(None, 24)
    ok_button_font = pygame.font.SysFont(None, 20)

# Input box variables
username_text = ""
password_text = ""
password_visible = False  # New variable to toggle password visibility
active_box = "username"  # Start with username active: "username", "password", "login_button", or None
feedback_message = ""  # For login feedback

# Text offset for scrolling
username_text_offset = 0
password_text_offset = 0

# Cursor blink variables
cursor_blink_timer = 0
cursor_visible = True
BLINK_INTERVAL = 500  # milliseconds

# Button press variables
login_button_pressed = False

# Small window variables
show_small_window = False
small_window_message = ""

# Backspace repeat variables
backspace_timer = 0
backspace_initial_delay = 500  # ms before starting repeat
backspace_repeat_delay = 100  # ms between repeats
backspace_held = False

# Mouse tracking for animation
mouse_x = WIDTH // 2
mouse_y = HEIGHT // 2

# Background shapes for animation
shapes = []

def create_triangle(cx, cy, size):
    """Create triangle points"""
    return [
        (cx, cy - size),
        (cx + size, cy + size),
        (cx - size, cy + size)
    ]

def create_hexagon(cx, cy, size):
    """Create hexagon points"""
    points = []
    for i in range(6):
        angle = i * 60 * math.pi / 180
        x = cx + size * math.cos(angle)
        y = cy + size * math.sin(angle)
        points.append((x, y))
    return points

def create_square(cx, cy, size):
    """Create square points"""
    return [
        (cx - size, cy - size),
        (cx + size, cy - size),
        (cx + size, cy + size),
        (cx - size, cy + size)
    ]

def create_circle(cx, cy, radius):
    """Create circle"""
    return (cx, cy, radius)

def generate_shapes():
    global shapes
    shapes = []
    for i in range(400):
        shape_type = random.choice(['triangle', 'hexagon', 'square', 'circle'])
        base_x = random.uniform(0, WIDTH)
        base_y = random.uniform(0, HEIGHT)
        size = random.randint(5, 15)
        color = random.choice(SHAPE_COLORS)
        
        shapes.append({
            'type': shape_type,
            'base_x': base_x,
            'base_y': base_y,
            'x': base_x,
            'y': base_y,
            'size': size,
            'color': color,
            'vx': 0,
            'vy': 0
        })

# Generate initial shapes
generate_shapes()

def draw_shapes(surface, shapes, mouse_x, mouse_y):
    """Draw all shapes with cursor attraction and shape repulsion"""
    
    for shape in shapes:
        total_fx = 0
        total_fy = 0
        
        # Repulsion from other shapes (faster repulsion)
        for other_shape in shapes:
            if shape is not other_shape:
                dx = shape['x'] - other_shape['x']
                dy = shape['y'] - other_shape['y']
                distance = math.sqrt(dx * dx + dy * dy) + 1
                
                repulsion_range = 80  # Range of repulsion
                if distance < repulsion_range:
                    # Repel away from other shapes (increased multiplier for faster repulsion)
                    repulsion = (repulsion_range - distance) / repulsion_range
                    total_fx += (dx / distance) * repulsion * 5  # Changed from 2 to 5
                    total_fy += (dy / distance) * repulsion * 5  # Changed from 2 to 5
        
        # Calculate force from cursor
        cursor_x = mouse_x
        cursor_y = mouse_y
        dx = cursor_x - shape['x']
        dy = cursor_y - shape['y']
        distance = math.sqrt(dx * dx + dy * dy) + 1
        
        cursor_strength = 250  # Cursor magnet strength
        if distance < cursor_strength:
            force = (cursor_strength - distance) / cursor_strength
            # Attraction to cursor
            total_fx += (dx / distance) * force * 4
            total_fy += (dy / distance) * force * 4
        
        # Return to base position when far from cursor
        base_dx = shape['base_x'] - shape['x']
        base_dy = shape['base_y'] - shape['y']
        base_distance = math.sqrt(base_dx * base_dx + base_dy * base_dy) + 1
        
        # Gentle return to base position
        if base_distance > 5:
            return_force = 0.02
            total_fx += (base_dx / base_distance) * return_force
            total_fy += (base_dy / base_distance) * return_force
        
        # Add damping
        shape['vx'] = shape['vx'] * 0.90 + total_fx * 0.10
        shape['vy'] = shape['vy'] * 0.90 + total_fy * 0.10
        
        # Update position
        shape['x'] += shape['vx']
        shape['y'] += shape['vy']
        
        # Draw shape
        if shape['type'] == 'triangle':
            points = create_triangle(shape['x'], shape['y'], shape['size'])
            pygame.draw.polygon(surface, shape['color'], points)
        elif shape['type'] == 'hexagon':
            points = create_hexagon(shape['x'], shape['y'], shape['size'])
            pygame.draw.polygon(surface, shape['color'], points)
        elif shape['type'] == 'square':
            points = create_square(shape['x'], shape['y'], shape['size'])
            pygame.draw.polygon(surface, shape['color'], points)
        elif shape['type'] == 'circle':
            pygame.draw.circle(surface, shape['color'], (int(shape['x']), int(shape['y'])), shape['size'])

def draw_cursor_magnet(surface, mouse_x, mouse_y):
    """Draw big solid black cursor magnet"""
    pygame.draw.circle(surface, (0, 0, 0), (int(mouse_x), int(mouse_y)), 12)

# Function to update all rect positions based on current WIDTH and HEIGHT
def update_rects():
    global username_box_rect, password_box_rect, forget_password_rect, sinup_text_rect, login_button_rect, small_window_rect, ok_button_rect, frame_rect, eye_button_rect
    frame_rect = pygame.Rect(WIDTH // 2 - 225, HEIGHT // 2 - 250, 450, 500)  # Centered frame (450px) around the form
    username_box_rect = pygame.Rect(frame_rect.left + 20, frame_rect.top + 200, 400, 40)
    password_box_rect = pygame.Rect(frame_rect.left + 20, frame_rect.top + 280, 400, 40)
    forget_password_rect = pygame.Rect(frame_rect.left + 20, frame_rect.top + 330, 160, 40)
    sinup_text_rect = pygame.Rect(frame_rect.left + 350, frame_rect.top + 330, 50, 20)  # Adjusted size and position
    login_button_rect = pygame.Rect(WIDTH // 2 - 50, frame_rect.top + 380, 100, 50)  # Login button remains centered
    small_window_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 100, 300, 200)
    ok_button_rect = pygame.Rect(small_window_rect.centerx - 30, small_window_rect.y + small_window_rect.height - 60, 60, 40)
    eye_button_rect = pygame.Rect(password_box_rect.right - 35, password_box_rect.y + 5, 30, 30)  # Eye button on the right side of password box

# Initial rect setup
update_rects()

# Clock for timing
clock = pygame.time.Clock()

# Main loop
running = True
while running:
    dt = clock.tick(60)  # 60 FPS
    cursor_blink_timer += dt
    if cursor_blink_timer >= BLINK_INTERVAL:
        cursor_visible = not cursor_visible
        cursor_blink_timer = 0

    # Get mouse position
    mouse_pos = pygame.mouse.get_pos()
    mouse_x, mouse_y = mouse_pos

    # Change cursor based on hover (for login UI)
    if show_small_window:
        if ok_button_rect.collidepoint(mouse_pos):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    elif eye_button_rect.collidepoint(mouse_pos):
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Arrow cursor for eye button
    elif username_box_rect.collidepoint(mouse_pos) or password_box_rect.collidepoint(mouse_pos):
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
    elif forget_password_rect.collidepoint(mouse_pos) or sinup_text_rect.collidepoint(mouse_pos) or login_button_rect.collidepoint(mouse_pos):
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # Handle held keys for backspace with MS-Word-like delay
    keys = pygame.key.get_pressed()
    if not show_small_window:
        if keys[pygame.K_BACKSPACE]:
            backspace_timer += dt
            if not backspace_held:
                if backspace_timer >= backspace_initial_delay:
                    backspace_held = True
                    backspace_timer = 0
            else:
                if backspace_timer >= backspace_repeat_delay:
                    backspace_timer = 0
                    if active_box == "username" and username_text:
                        username_text = username_text[:-1]
                    elif active_box == "password" and password_text:
                        password_text = password_text[:-1]
        else:
            backspace_held = False
            backspace_timer = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            update_rects()  # Update all rect positions
            generate_shapes()  # Regenerate shapes to cover the new screen size
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if show_small_window:
                if ok_button_rect.collidepoint(event.pos):
                    show_small_window = False
            else:
                # Check if clicked on eye button
                if eye_button_rect.collidepoint(event.pos):
                    password_visible = not password_visible  # Toggle password visibility
                # Check if clicked on username box
                elif username_box_rect.collidepoint(event.pos):
                    active_box = "username"
                    feedback_message = ""  # Clear feedback when editing
                elif password_box_rect.collidepoint(event.pos):
                    active_box = "password"
                    feedback_message = ""  # Clear feedback when editing
                elif login_button_rect.collidepoint(event.pos):
                    active_box = "login_button"
                    login_button_pressed = True
                    feedback_message = ""  # Clear feedback when editing
                elif forget_password_rect.collidepoint(event.pos):
                    # Handle forget password click (for now, just show a message)
                    feedback_message = "Forgot Password clicked!"
                elif sinup_text_rect.collidepoint(event.pos):
                    # Handle sinup click (for now, just show a message)
                    feedback_message = "Sinup clicked!"
                else:
                    active_box = None
        elif event.type == pygame.MOUSEBUTTONUP:
            if login_button_pressed and login_button_rect.collidepoint(event.pos):
                # Handle login submission on button up
                if not username_text and not password_text:
                    feedback_message = "All fields are required."
                elif username_text.upper() == "AASHIQUE" and password_text == "1234567890":
                    small_window_message = f"Welcome! {username_text} Sir!"
                    show_small_window = True
                elif username_text.upper() == "HARSHITA" and password_text == "1234567890":
                    small_window_message = f"Welcome! {username_text} Mam!"
                    show_small_window = True
                elif username_text.upper() == "MAYANK" and password_text == "1234567890":
                    small_window_message = f"Welcome! {username_text} Sir!"
                    show_small_window = True
                else:
                    feedback_message = "Invalid Username or Password. Please try again!"
            login_button_pressed = False
        elif event.type == pygame.KEYDOWN:
            if not show_small_window:  # Only handle keyboard for login form
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # Enter key: if on login_button, submit; else, move to next
                    if active_box == "login_button":
                        # Handle login submission
                        if not username_text and not password_text:
                            feedback_message = "All fields are required."
                        elif username_text.upper() == "AASHIQUE" and password_text == "1234567890":
                            small_window_message = f"Welcome! {username_text} Sir!"
                            show_small_window = True
                        elif username_text.upper() == "HARSHITA" and password_text == "1234567890":
                            small_window_message = f"Welcome! {username_text} Mam!"
                            show_small_window = True
                        elif username_text.upper() == "MAYANK" and password_text == "1234567890":
                            small_window_message = f"Welcome! {username_text} Sir!"
                            show_small_window = True
                        else:
                            feedback_message = "Invalid Username or Password. Please try again!"
                    elif active_box == "username":
                        active_box = "password"
                    elif active_box == "password":
                        active_box = "login_button"
                    feedback_message = ""  # Clear feedback when navigating
                elif active_box == "username":
                    if event.key == pygame.K_BACKSPACE:
                        username_text = username_text[:-1]
                        backspace_held = False  # Reset on keydown
                        backspace_timer = 0
                    elif event.unicode.isalnum() or event.unicode == '_' or event.unicode == ' ':  # Accept alphabets, numerics, underscore, and space
                        username_text += event.unicode.upper()  # Convert to uppercase
                elif active_box == "password":
                    if event.key == pygame.K_BACKSPACE:
                        password_text = password_text[:-1]
                        backspace_held = False  # Reset on keydown
                        backspace_timer = 0
                    elif event.unicode.isprintable():  # Only accept printable characters
                        password_text += event.unicode

    # Calculate text offsets for scrolling
    if username_text:
        username_text_width = input_font.size(username_text)[0]
        if username_text_width > username_box_rect.width - 10:  # 10 for padding
            username_text_offset = username_text_width - (username_box_rect.width - 10)
        else:
            username_text_offset = 0
    else:
        username_text_offset = 0

    if password_text:
        if password_visible:
            password_display = password_text
        else:
            password_display = "*" * len(password_text)
        password_text_width = input_font.size(password_display)[0]
        if password_text_width > password_box_rect.width - 50:  # Adjust for eye button space
            password_text_offset = password_text_width - (password_box_rect.width - 50)
        else:
            password_text_offset = 0
    else:
        password_text_offset = 0

    # Fill the screen with background animation
    screen.fill(BG_COLOR)
    
    # Draw shapes with cursor attraction
    draw_shapes(screen, shapes, mouse_x, mouse_y)
    
    # Draw cursor magnet
    draw_cursor_magnet(screen, mouse_x, mouse_y)

    # Draw rounded frame fill
    pygame.draw.rect(screen, DARK_GRAY, frame_rect, border_radius=20)

    # Original window content
    # "Login" - centered at top
    login_text = login_font.render("Login", True, PINK)
    login_rect = login_text.get_rect(center=(WIDTH // 2, frame_rect.top + 80))
    screen.blit(login_text, login_rect)

        # "Welcome Back" - centered at frame
    welcome_text = welcome_font.render("Welcome Back", True, WHITE)
    welcome_rect = welcome_text.get_rect(center=(WIDTH // 2, frame_rect.top + 140))
    screen.blit(welcome_text, welcome_rect)

    # "Username" - left-aligned at frame
    username_label = label_font.render("Username", True, LIGHT_GRAY)
    username_label_rect = username_label.get_rect(left=frame_rect.left + 30, top=frame_rect.top + 170)
    screen.blit(username_label, username_label_rect)

    # Input box for Username
    pygame.draw.rect(screen, "#E7E6E6", username_box_rect, border_radius=10)  # Rounded fill
    if active_box == "username":
        pygame.draw.rect(screen, GRAY, username_box_rect, 2, border_radius=10)  # Rounded highlight border
    else:
        pygame.draw.rect(screen, BLACK, username_box_rect, 2, border_radius=10)  # Rounded normal border
    # Set clip for text
    screen.set_clip(username_box_rect)
    # Render username text or placeholder
    if username_text:
        username_input_text = input_font.render(username_text, True, BLACK)
        screen.blit(username_input_text, (username_box_rect.x + 5 - username_text_offset, username_box_rect.y + 10))
        # Draw blinking cursor if active
        if active_box == "username" and cursor_visible:
            cursor_x = username_box_rect.x + 5 + username_input_text.get_width() - username_text_offset
            cursor_y = username_box_rect.y + 10
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + input_font.get_height()), 2)
    else:
        username_input_text = input_font.render("Enter username", True, GRAY)
        screen.blit(username_input_text, (username_box_rect.x + 5, username_box_rect.y + 10))
        if active_box == "username" and cursor_visible:
            cursor_x = username_box_rect.x + 5
            cursor_y = username_box_rect.y + 10
            pygame.draw.line(screen, GRAY, (cursor_x, cursor_y), (cursor_x, cursor_y + input_font.get_height()), 2)
    # Unset clip
    screen.set_clip(None)

    # "Password" - left-aligned at frame
    password_label = label_font.render("Password", True, LIGHT_GRAY)
    password_label_rect = password_label.get_rect(left=frame_rect.left + 30, top=frame_rect.top + 250)
    screen.blit(password_label, password_label_rect)

    # Input box for Password
    pygame.draw.rect(screen, "#E7E6E6", password_box_rect, border_radius=10)  # Rounded fill
    if active_box == "password":
        pygame.draw.rect(screen, GRAY, password_box_rect, 2, border_radius=10)  # Rounded highlight border
    else:
        pygame.draw.rect(screen, BLACK, password_box_rect, 2, border_radius=10)  # Rounded normal border
    # Set clip for text
    screen.set_clip(password_box_rect)
    # Render password text (masked with asterisks or visible) or placeholder
    if password_text:
        if password_visible:
            password_display = password_text
        else:
            password_display = "*" * len(password_text)
        password_input_text = input_font.render(password_display, True, BLACK)
        screen.blit(password_input_text, (password_box_rect.x + 5 - password_text_offset, password_box_rect.y + 10))
        # Draw blinking cursor if active
        if active_box == "password" and cursor_visible:
            cursor_x = password_box_rect.x + 5 + password_input_text.get_width() - password_text_offset
            cursor_y = password_box_rect.y + 10
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + input_font.get_height()), 2)
    else:
        password_input_text = input_font.render("Enter password", True, GRAY)
        screen.blit(password_input_text, (password_box_rect.x + 5, password_box_rect.y + 10))
        if active_box == "password" and cursor_visible:
            cursor_x = password_box_rect.x + 5
            cursor_y = password_box_rect.y + 10
            pygame.draw.line(screen, GRAY, (cursor_x, cursor_y), (cursor_x, cursor_y + input_font.get_height()), 2)
    # Unset clip
    screen.set_clip(None)

    # Eye button for password visibility
    eye_color = BLUE if eye_button_rect.collidepoint(mouse_pos) else LIGHT_GRAY
    pygame.draw.circle(screen, eye_color, eye_button_rect.center, 12)  # Simple circle for eye button
    pygame.draw.circle(screen, BLACK, eye_button_rect.center, 12, 2)  # Border
    # Draw a simple eye icon (circle with dot)
    pygame.draw.circle(screen, BLACK, eye_button_rect.center, 5)
    pygame.draw.circle(screen, WHITE, eye_button_rect.center, 2)

    # Forget Password text (left-aligned at frame)
    forget_password_text = link_font.render("Forgot Password", True, WHITE if forget_password_rect.collidepoint(mouse_pos) else GRAY)
    forget_password_text_rect = forget_password_text.get_rect(left=frame_rect.left + 30, top=frame_rect.top + 330)
    screen.blit(forget_password_text, forget_password_text_rect)

    # Sinup text (left-aligned at frame)
    sinup_text = link_font.render("Sinup", True, WHITE if sinup_text_rect.collidepoint(mouse_pos) else GRAY)
    sinup_text_text_rect = sinup_text.get_rect(left=frame_rect.left + 355, top=frame_rect.top + 330)
    screen.blit(sinup_text, sinup_text_text_rect)

    # Login button (centered, rounded)
    if login_button_pressed:
        button_color = GRAY
    else:
        button_color = '#FF3399'
    pygame.draw.rect(screen, button_color, login_button_rect, border_radius=15)  # Rounded fill
    pygame.draw.rect(screen, BLACK, login_button_rect, 2, border_radius=15)  # Rounded border
    login_button_text = button_font.render("Login", True, BLACK)
    login_button_text_rect = login_button_text.get_rect(center=login_button_rect.center)
    screen.blit(login_button_text, login_button_text_rect)

    # Feedback message (centered, below login button with space)
    if feedback_message:
        if "successful" in feedback_message:
            feedback_color = GREEN
        else:
            feedback_color = RED
        feedback_text = feedback_font.render(feedback_message, True, feedback_color)
        feedback_rect = feedback_text.get_rect(center=(WIDTH // 2, login_button_rect.bottom + 20))
        screen.blit(feedback_text, feedback_rect)

    # Small window overlay
    if show_small_window:
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(TRANSPARENT_BLACK)
        screen.blit(overlay, (0, 0))

        # Small window box
        pygame.draw.rect(screen, WHITE, small_window_rect)
        pygame.draw.rect(screen, BLACK, small_window_rect, 2)  # Border

        # Small window message
        small_text = popup_font.render(small_window_message, True, BLACK)
        small_text_rect = small_text.get_rect(center=(small_window_rect.centerx, small_window_rect.centery - 20))
        screen.blit(small_text, small_text_rect)

        # OK button (centered horizontally)
        pygame.draw.rect(screen, LIGHT_GRAY, ok_button_rect)
        pygame.draw.rect(screen, BLACK, ok_button_rect, 2)  # Border
        ok_text = ok_button_font.render("OK", True, BLACK)
        ok_text_rect = ok_text.get_rect(center=ok_button_rect.center)
        screen.blit(ok_text, ok_text_rect)

    # Update the display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
sys.exit()