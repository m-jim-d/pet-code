#!/usr/bin/env python3

# Filename: A02_air_track_framework.py

# Python
import sys, os
import pygame
import datetime

# PyGame Constants
from pygame.locals import K_ESCAPE, K_1, K_2, K_3, K_4, K_5
from pygame.color import THECOLORS

#=====================================================================
# Classes
#=====================================================================

class GameWindow:
    def __init__(self, screen_tuple_px):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]

        # Create a reference to display's surface object. This object is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)
        
        # Paint screen black.
        self.erase_and_update()
        
    def update_caption(self, title):
        pygame.display.set_caption(title)
        self.caption = title
        
    def erase_and_update(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.flip()
        

class Detroit:
    def __init__(self, color=THECOLORS["white"], left_px=10, width_px=26, height_px=98, speed_mps=1):
        
        self.color = color
        
        self.height_px = height_px        
        self.top_px    = game_window.height_px - self.height_px
        self.width_px  = width_px
        
        self.width_m = env.m_from_px( width_px)
        self.halfwidth_m = self.width_m/2.0
        
        self.height_m = env.m_from_px( height_px)
        
        # Initialize the position and speed of the car. These are affected by the
        # physics calcs in the Track.
        self.center_m = env.m_from_px(left_px) + self.halfwidth_m
        self.speed_mps = speed_mps
                
        # Create a rectangle object based on these dimensions
        # Left: distance from the left edge of the screen in px.
        # Top:  distance from the top  edge of the screen in px.
        self.rect = pygame.Rect(left_px, self.top_px, self.width_px, self.height_px)
    
    def draw_car(self):
        # Update the pixel position of the car's rectangle object to match the value
        # controlled by the physics calculations.
        self.rect.centerx = env.px_from_m( self.center_m)
        
        # Draw the main rectangle.
        pygame.draw.rect(game_window.surface, self.color, self.rect)

        
class AirTrack:
    def __init__(self):
        # Initialize the list of cars.
        self.cars = []

    def update_SpeedandPosition(self, car, dt_s):
        # Calculate the new physical car position
        car.center_m = car.center_m + (car.speed_mps * dt_s)
        
    def make_some_cars(self, nmode):
        # Clear out any existing cars
        self.cars = []
        
        # Create a filtered list of vibrant colors
        vibrant_colors = []
        for color_name, color_value in THECOLORS.items():
            # Skip colors that are too close to gray
            r, g, b = color_value[:3]  # Get RGB values
            # Skip if all RGB values are too close together (indicates grayscale)
            if not (abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30):
                vibrant_colors.append(color_value)
        
        if (nmode == 1):
            self.cars.append( Detroit(color=THECOLORS["red"], left_px = 240, speed_mps=  0.2))
            self.cars.append( Detroit(color=THECOLORS["blue"], left_px = 340, speed_mps= -0.2))
            
        elif (nmode == 2):
            self.cars.append( Detroit(color=THECOLORS["yellow"], left_px = 240, speed_mps= -0.1))
            self.cars.append( Detroit(color=THECOLORS["green"],   left_px = 440, speed_mps= -0.2))
            
        elif (nmode == 3):
            n_colors = 20
            for j in range(min(n_colors, len(vibrant_colors))):
                self.cars.append( Detroit(color=vibrant_colors[j], width_px=15, left_px=450, 
                                       speed_mps=0.05*(j-n_colors/2.0)) )
            
        elif (nmode == 4):
            n_colors = 180
            for j in range(min(n_colors, len(vibrant_colors))):
                self.cars.append( Detroit(color=vibrant_colors[j], width_px=15, left_px=450, 
                                       speed_mps=0.01*(j-n_colors/2.0)) )
            
        elif (nmode == 5):
            n_colors = 300
            for j in range(min(n_colors, len(vibrant_colors))):
                self.cars.append( Detroit(color=vibrant_colors[j], width_px=15, left_px=450, 
                                       speed_mps=0.01*(j-n_colors/2.0)) )
        
        # Update the caption at the top of the pygame window frame.
        game_window.update_caption("Air Track (basic): Demo #" + str(nmode)) 


class Environment:
    def __init__(self, length_px, length_m):
        self.px_to_m = length_m/length_px
        self.m_to_px = length_px/length_m
    
    # Convert from meters to pixels
    def px_from_m(self, dx_m):
        return round(dx_m * self.m_to_px)
    
    # Convert from pixels to meters
    def m_from_px(self, dx_px):
        return dx_px * self.px_to_m
        
    def get_local_user_input(self):
        
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                return 'quit'
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    return 'quit'
                elif (event.key==K_1):            
                    return 1           
                elif (event.key==K_2):                          
                    return 2
                elif (event.key==K_3):                          
                    return 3
                elif (event.key==K_4):                          
                    return 4
                elif (event.key==K_5):                          
                    return 5
                else:
                    return "Nothing set up for this key."
            
            elif (event.type == pygame.KEYUP):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONDOWN):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONUP):
                pass
                
#============================================================
# Main procedural functions.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_track
    
    # Initiate pygame
    pygame.init()

    # Tuple to define window dimensions
    window_size_px = window_width_px, window_height_px = (950, 120)

    # Instantiate an Environment object for converting back and forth from pixels and meters.
    # The also creates the local client.
    env = Environment(window_width_px, 1.5)

    # Instantiate the window.
    game_window = GameWindow(window_size_px)

    # Instantiate an air track (this adds an empty car list to the track).
    air_track = AirTrack()

    # Make some cars (run demo #1).
    air_track.make_some_cars(1)

    # Instantiate clock to help control the framerate.
    myclock = pygame.time.Clock()
        
    # Control the framerate.
    framerate_limit = 400

    time_s = 0.0
    user_done = False
    
    while not user_done:
        
        # Erase everything.
        game_window.surface.fill(THECOLORS["black"])

        # Get the delta t for one frame (this changes depending on system load).
        dt_s = myclock.tick(framerate_limit) * 1e-3
        
        # Check for user initiated stop or demo change.
        resetmode = env.get_local_user_input()
        if (resetmode in [0,1,2,3,4,5,6,7,8,9]):
            print("reset mode =", resetmode)
            
            # This should remove all references to the cars and effectively deletes them.
            air_track.cars = []
            
            # Now just black everything out and update the screen.
            game_window.erase_and_update()
            
            # Build new set of cars based on the reset mode.
            air_track.make_some_cars( resetmode)
        
        elif (resetmode == 'quit'):
            user_done = True
            
        elif (resetmode != None):
            print(resetmode)
        
        # Update speed and x position of each car based on the dt_s for this frame.
        for car in air_track.cars:
            air_track.update_SpeedandPosition(car, dt_s)
            
        # Draw the car at the new position.
        for car in air_track.cars:
            car.draw_car()
        
        # Update the total time since starting.
        time_s += dt_s
        
        # Make this update visible on the screen.
        pygame.display.flip()
            
#============================================================
# Run the main program.    
#============================================================

main()