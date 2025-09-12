import time
import evdev
import random
import fcntl
import os
import json
from plasma import auto
from evdev import InputDevice, ecodes

# The number of lights on your Plasma device.
NUM_LIGHTS = 9
# This assumes 4 pixels per button light, as per the documentation.
PIXELS_PER_BUTTON = 4
NUM_PIXELS = NUM_LIGHTS * PIXELS_PER_BUTTON

# The total duration of the game in seconds.
GAME_DURATION = 30
# The fixed time a mole will stay active.
MOLE_DURATION = 1.0
# The duration of the red penalty flash.
PENALTY_FLASH_DURATION = 0.2
# The time for each countdown flash.
COUNTDOWN_FLASH_DURATION = 0.5

# The file to write the game state to
GAME_STATE_FILE = "game_state.json"

# Initialize the Plasma device with the total number of pixels.
plasma = auto(default=f"GPIO:14:15:pixel_count={NUM_PIXELS}")
# Set all lights to off at the start.
plasma.set_all(0, 0, 0)
plasma.show()

# A dictionary mapping keycodes to their corresponding light index (0-8).
KEY_TO_LIGHT_INDEX = {
    ecodes.KEY_1: 0,
    ecodes.KEY_2: 1,
    ecodes.KEY_3: 2,
    ecodes.KEY_4: 3,
    ecodes.KEY_5: 4,
    ecodes.KEY_6: 5,
    ecodes.KEY_7: 6,
    ecodes.KEY_8: 7,
    ecodes.KEY_9: 8,
}

# The path to your input device.
device_path = '/dev/input/event0'

# A list of colors to use for the moles.
MOLE_COLOR = (0, 255, 0) # Green

def write_game_state(state):
    """Writes the current game state to a JSON file."""
    try:
        with open(GAME_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Failed to write game state to file: {e}")

def get_pixel_indices_for_light(light_index):
    """
    Calculates the starting and ending pixel indices for a given light.
    """
    start = light_index * PIXELS_PER_BUTTON
    end = start + PIXELS_PER_BUTTON
    return start, end

def light_up_mole(light_index):
    """
    Lights up a specific button with the single mole color.
    """
    start_pixel, end_pixel = get_pixel_indices_for_light(light_index)
    for i in range(start_pixel, end_pixel):
        plasma.set_pixel(i, MOLE_COLOR[0], MOLE_COLOR[1], MOLE_COLOR[2], brightness=0.25)
    plasma.show()

def turn_off_mole(light_index):
    """
    Turns off a specific button.
    """
    if light_index is not None:
        start_pixel, end_pixel = get_pixel_indices_for_light(light_index)
        for i in range(start_pixel, end_pixel):
            plasma.set_pixel(i, 0, 0, 0, brightness=0.25)
        plasma.show()

def light_up_all_red():
    """
    Lights up all buttons with a red color for a short duration.
    """
    plasma.set_all(255, 0, 0, brightness=0.25) # Set to red
    plasma.show()
    time.sleep(PENALTY_FLASH_DURATION)
    plasma.set_all(0, 0, 0, brightness=0.25) # Turn all lights off
    plasma.show()

def countdown_sequence():
    """
    Performs a visual countdown before the game starts.
    """
    # Flash all buttons blue as a "ready" signal.
    plasma.set_all(0, 0, 255, brightness=0.25) # Blue
    plasma.show()
    time.sleep(COUNTDOWN_FLASH_DURATION * 2)
    plasma.set_all(0, 0, 0, brightness=0.25)
    time.sleep(COUNTDOWN_FLASH_DURATION)

    # Flash a white countdown (3, 2, 1) on the first three buttons.
    for i in range(3, 0, -1):
        # Lights up a button white for the countdown
        light_up_pixel_group(i - 1, (255, 255, 255))
        print(f"{i}...")
        write_game_state({'state': 'countdown', 'time': i})
        time.sleep(COUNTDOWN_FLASH_DURATION)
        turn_off_mole(i - 1)
        time.sleep(COUNTDOWN_FLASH_DURATION)
    
    print("GO!")

def light_up_pixel_group(light_index, color):
    """
    Helper function to light up a group of pixels with a specific color.
    """
    start_pixel, end_pixel = get_pixel_indices_for_light(light_index)
    for i in range(start_pixel, end_pixel):
        plasma.set_pixel(i, color[0], color[1], color[2], brightness=0.25)
    plasma.show()

try:
    # Open the input device and set it to non-blocking mode.
    dev = InputDevice(device_path)
    fd = dev.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    print(f"Listening for events on {device_path}...")
    
    # The main game loop will run indefinitely, restarting the game when it ends.
    while True:
        # Game variables are reset for each new game.
        score = 0
        game_over = False
        active_mole_light_index = None
        last_mole_time = 0
        can_process_input = True
        
        write_game_state({'state': 'start_screen'})

        print("\n" + "="*20)
        print("Whack-A-Mole Game")
        print("="*20)
        print("Press the '5' button to start...")
        
        # Turn off all lights and only light up button 5
        plasma.set_all(0, 0, 0, brightness=0.25)
        light_up_pixel_group(KEY_TO_LIGHT_INDEX[ecodes.KEY_5], (255, 255, 255))

        # Wait for the '5' button press to start the game.
        start_pressed = False
        while not start_pressed:
            try:
                for event in dev.read():
                    if event.type == ecodes.EV_KEY and event.value == 1 and event.code == ecodes.KEY_5:
                        start_pressed = True
                        print("Button 5 pressed. Starting game...")
                        write_game_state({'state': 'game_start'})
                        break
            except (IOError, BlockingIOError):
                pass
        
        # Run the countdown sequence after a button is pressed.
        countdown_sequence()

        game_start_time = time.time()

        # The inner game loop. This runs for the duration of the game.
        while not game_over:
            current_time = time.time()
            time_elapsed = current_time - game_start_time

            # Check for game end condition.
            if time_elapsed >= GAME_DURATION:
                game_over = True
                can_process_input = False
                break
            
            # If there's no mole or the current mole's time is up, spawn a new one.
            if active_mole_light_index is None or (current_time - last_mole_time) > MOLE_DURATION:
                if active_mole_light_index is not None:
                    print("Miss! Mole got away.")
                    turn_off_mole(active_mole_light_index)
                    
                new_mole_index = random.randint(0, NUM_LIGHTS - 1)
                active_mole_light_index = new_mole_index
                light_up_mole(active_mole_light_index)
                last_mole_time = current_time
                
                # Write mole and score update to file
                write_game_state({
                    'state': 'playing',
                    'mole_index': active_mole_light_index,
                    'score': score,
                    'time_left': round(GAME_DURATION - time_elapsed, 1)
                })

            # Try to read events from the input device without blocking.
            if can_process_input:
                try:
                    for event in dev.read():
                        if event.type == ecodes.EV_KEY and event.value == 1:
                            # Only register inputs when a mole is lit up
                            if active_mole_light_index is not None and event.code in KEY_TO_LIGHT_INDEX:
                                pressed_light_index = KEY_TO_LIGHT_INDEX[event.code]

                                if pressed_light_index == active_mole_light_index:
                                    score += 1
                                    print(f"Hit! Score: {score}")
                                    turn_off_mole(active_mole_light_index)
                                    active_mole_light_index = None
                                    write_game_state({'state': 'hit', 'score': score})
                                else:
                                    score = max(0, score - 0.5) # Deduct 0.5 points
                                    print(f"Miss! That was not the right button. Score: {score}")
                                    light_up_all_red()
                                    turn_off_mole(active_mole_light_index)
                                    active_mole_light_index = None
                                    write_game_state({'state': 'miss', 'score': score})
                                
                                # Send updated state to file
                                write_game_state({
                                    'state': 'playing',
                                    'mole_index': active_mole_light_index,
                                    'score': score,
                                    'time_left': round(GAME_DURATION - time_elapsed, 1)
                                })
                                
                except (IOError, BlockingIOError):
                    # No events to read, continue with the loop.
                    pass
        
        # Game over, display final score.
        turn_off_mole(active_mole_light_index)
        
        # Light up all buttons white at the end of the game
        plasma.set_all(255, 255, 255, brightness=0.25)
        plasma.show()
        
        print("-" * 20)
        print(f"Game Over! Your final score is: {score}")
        print("-" * 20)
        
        # Write final score to file
        write_game_state({'state': 'game_over', 'score': score})
        
        print("\nGame restarting in 5 seconds...")
        time.sleep(5)
        plasma.set_all(0, 0, 0, brightness=0.25)
        plasma.show()

except FileNotFoundError:
    print(f"Error: Could not find device at {device_path}. Make sure the device is connected and you have the correct permissions (e.g., run with sudo).")
except KeyboardInterrupt:
    print("\nKeyboard interrupt detected. Clearing LEDs and exiting gracefully.")
    plasma.set_all(0, 0, 0)
    plasma.show()
except Exception as e:
    print(f"An error occurred: {e}")
