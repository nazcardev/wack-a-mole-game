import pygame
import sys
import os
import json
import time

# --- Game Constants ---
WHITE = (255, 255, 255)
MOLE_COLOR = (0, 255, 0)
PENALTY_COLOR = (255, 0, 0)
NUM_MOLES = 9
FONT_SIZE = 40
SCORE_FONT_COLOR = (255, 255, 255)
GAME_OVER_FONT_COLOR = (255, 255, 255)
COUNTDOWN_FONT_COLOR = (255, 255, 255)
ELAPSED_TIME_FONT_COLOR = (255, 255, 255)
GAME_DURATION = 30 # The total duration of the game in seconds

# --- Pygame Initialization ---
pygame.init()

# Set display mode to fullscreen
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()

pygame.display.set_caption("Pygame Whack-A-Mole Visualizer")
clock = pygame.time.Clock()
font = pygame.font.Font(None, FONT_SIZE)
small_font = pygame.font.Font(None, 30) # A smaller font for the elapsed time

# The file to read the game state from
GAME_STATE_FILE = "game_state.json"

# --- Image Assets ---
try:
    # Load and scale the background image to fit the screen
    background_image = pygame.image.load('background.png').convert()
    background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))

    # Load and scale the mole image
    mole_image = pygame.image.load('mole.png').convert_alpha()
    mole_image = pygame.transform.scale(mole_image, (100, 100))

except pygame.error as e:
    print(f"Could not load image file: {e}")
    sys.exit()

# --- Game State Variables ---
mole_positions = []
# Adjust spacing to center the images
MOLE_SPACING_X = (WIDTH - 3 * mole_image.get_width()) // 4
MOLE_SPACING_Y = (HEIGHT - 3 * mole_image.get_height()) // 4

for row in range(3):
    for col in range(3):
        x = MOLE_SPACING_X + col * (mole_image.get_width() + MOLE_SPACING_X)
        y = MOLE_SPACING_Y + row * (mole_image.get_height() + MOLE_SPACING_Y)
        mole_rect = mole_image.get_rect(center=(x + mole_image.get_width() / 2, y + mole_image.get_height() / 2))
        mole_positions.append(mole_rect)

active_mole_index = None
current_score = 0
time_left = 0
game_state = "waiting"
start_time = None # New variable to store the start time for the elapsed timer

def draw_moles(start_mode=False, hit_mode=False, miss_mode=False):
    """Draw all moles and the background, highlighting the active one with an image."""
    # Draw the background first
    screen.blit(background_image, (0, 0))
    
    # NOTE: The mole holes are now part of the background image, so they are not drawn here.

    if start_mode:
        # On the start screen, show a mole on the center button
        center_mole_rect = mole_image.get_rect(center=mole_positions[4].center)
        screen.blit(mole_image, center_mole_rect)
    elif hit_mode:
        # On a hit, show all moles briefly as a celebratory flash
        for pos in mole_positions:
            mole_rect = mole_image.get_rect(center=pos.center)
            screen.blit(mole_image, mole_rect)
    elif miss_mode:
        # On a miss, flash red by drawing a semi-transparent red surface over everything
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(128) # Transparency
        s.fill(PENALTY_COLOR)
        screen.blit(s, (0,0))
    else:
        # In playing mode, draw the active mole.
        if active_mole_index is not None:
            mole_rect = mole_image.get_rect(center=mole_positions[active_mole_index].center)
            screen.blit(mole_image, mole_rect)

def read_game_state():
    """Reads the game state from the shared file."""
    global active_mole_index, current_score, time_left, game_state, start_time

    if not os.path.exists(GAME_STATE_FILE):
        return

    try:
        with open(GAME_STATE_FILE, 'r') as f:
            state_data = json.load(f)
            new_game_state = state_data.get('state', 'waiting')
            
            # Check if the game state is transitioning to "playing"
            if game_state != "playing" and new_game_state == "playing":
                # Start the elapsed time counter
                start_time = time.time()
                
            game_state = new_game_state
            active_mole_index = state_data.get('mole_index')
            current_score = state_data.get('score', 0)
            time_left = state_data.get('time_left', 0)
            
    except (IOError, json.JSONDecodeError):
        # File is being written to or is not a valid JSON. Ignore and try again next frame.
        pass

# --- Main Game Loop ---
try:
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        read_game_state()

        # Always draw the background first in the main loop
        screen.blit(background_image, (0, 0))

        if game_state == "waiting":
            text = font.render("Waiting for the physical game to start...", True, WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(text, text_rect)
        elif game_state == "start_screen":
            draw_moles(start_mode=True)
            text = font.render("Press '5' on the board to start!", True, WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
            screen.blit(text, text_rect)
        elif game_state == "countdown":
            text = font.render(str(time_left), True, COUNTDOWN_FONT_COLOR)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(text, text_rect)
        elif game_state == "playing":
            draw_moles()
            # Draw score on the screen
            score_text = font.render(f"Score: {current_score:.0f}", True, SCORE_FONT_COLOR)
            screen.blit(score_text, (50, 50))
            
            # New elapsed time display
            elapsed_time = time.time() - start_time
            remaining_time = max(0, GAME_DURATION - elapsed_time) # Ensure time doesn't go below 0
            
            seconds = int(remaining_time)
            milliseconds = int((remaining_time * 1000) % 1000)
            
            elapsed_time_str = f"{seconds:02d}:{milliseconds:03d}"
            elapsed_time_text = small_font.render(f"Time: {elapsed_time_str}", True, ELAPSED_TIME_FONT_COLOR)
            
            # Reposition the elapsed time text to the top-right
            elapsed_time_rect = elapsed_time_text.get_rect(topright=(WIDTH - 50, 50))
            screen.blit(elapsed_time_text, elapsed_time_rect)
            
        elif game_state == "hit":
            draw_moles(hit_mode=True)
        elif game_state == "miss":
            draw_moles(miss_mode=True)
        elif game_state == "game_over":
            game_over_text = font.render("Game Over!", True, GAME_OVER_FONT_COLOR)
            score_text = font.render(f"Final Score: {current_score:.0f}", True, GAME_OVER_FONT_COLOR)
            game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            screen.blit(game_over_text, game_over_rect)
            screen.blit(score_text, score_rect)

        pygame.display.flip()
        clock.tick(60)

except KeyboardInterrupt:
    print("\nKeyboard interrupt detected. Exiting gracefully.")
finally:
    pygame.quit()
    sys.exit()
