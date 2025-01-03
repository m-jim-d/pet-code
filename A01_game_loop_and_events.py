#!/usr/bin/env python3

# Filename: A01_game_loop_and_events.py

import sys, os
import pygame

# PyGame Constants
from pygame.locals import K_ESCAPE, K_e, K_f
from pygame.color import THECOLORS

# Initialize the Pygame environment.
pygame.init()

# Create a display surface to write to.
display_surface = pygame.display.set_mode((600,400))

# Instantiate a clock to help control the framerate.
myclock = pygame.time.Clock()

# Set the intial color of the whole pygame window.
display_surface.fill(THECOLORS["white"])

# Initialize some variables.
framerate_limit = 120
time_s = 0.0
key_e = "U"
key_f = "U"
user_done = False
mouse_button_UD = "U"

while not user_done:

    dt_s = float(myclock.tick( framerate_limit) * 1e-3)
    #myclock.tick(framerate_limit)
    
    #=====================================================
    # Get user input
    #=====================================================
    
    # loop through the list of events in the event queue.
    for event in pygame.event.get():
        
        # This main "if" structure checks the event type of each event.
        # Depending on the event type (QUIT, KEYDOWN, KEYUP, MOUSEBUTTONDOWN, or
        # MOUSEBUTTONUP), addition checks are made to identify the characteristics of the
        # event.
        if (event.type == pygame.QUIT): 
            user_done = True
        
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                user_done = True
            elif (event.key==K_e):
                key_e = 'D'
            elif (event.key==K_f):
                key_f = 'D'
                
        elif (event.type == pygame.KEYUP):
            if (event.key==K_e):
                key_e = 'U'
            elif (event.key==K_f):
                key_f = 'U'
        
        elif (event.type == pygame.MOUSEBUTTONDOWN):
            mouse_button_UD = 'D'
            
            # The get_pressed method returns T/F values in a tuple.
            (button1, button2, button3) = pygame.mouse.get_pressed()
            
            if button1:
                mouse_button = 1
            elif button2:
                mouse_button = 2
            elif button3:
                mouse_button = 3
            else:
                mouse_button = 0
                    
        elif (event.type == pygame.MOUSEBUTTONUP):
            mouse_button_UD = 'U'

    # Get the cursor position: x,y. Return this as a tuple.
    mouse_xy = pygame.mouse.get_pos()
    
    #=====================================================
    # End of user input collection
    #=====================================================
    
    # Erase the screen if the "d" key is pressed. Do this by filling the entire
    # screen with grey color.
    if (key_e == 'D'):
        display_surface.fill(THECOLORS["grey"])
    
    # Determine the color for the circle based on if a mouse button is up (U) or down (D).
    if ((mouse_button_UD == 'D') and (mouse_button == 1)):
        circle_color = THECOLORS["yellow"]
    elif ((mouse_button_UD == 'D') and (mouse_button == 2)):
        circle_color = THECOLORS["magenta"]
    elif ((mouse_button_UD == 'D') and (mouse_button == 3)):
        circle_color = THECOLORS["red"]
    else:
        circle_color = THECOLORS["blue"]
    
    # Draw the circle
    pygame.draw.circle(display_surface, circle_color, mouse_xy, 10, 0)
    
    # Add the incremental time to our time variable.
    time_s += dt_s
    
    # Print to the command window.
    print( f"{time_s:.1f}, {dt_s:.3f}, {myclock.get_fps():.0f}")
    
    # If the "f" key is up (not Down), update the entire display window. 
    if (key_f != 'D'):
        pygame.display.flip()