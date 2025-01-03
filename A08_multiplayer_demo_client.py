#!/usr/bin/env python3

# Filename: A08_multiplayer_demo_client.py

import sys, os
import pygame

# PyGame Constants
from pygame.locals import (
    K_ESCAPE,
    K_c, K_1, K_2, K_3,
    K_a, K_s, K_d, K_w,
    K_j, K_k, K_l, K_i, K_SPACE,
    K_LSHIFT, K_t
)
from pygame.color import THECOLORS

import argparse

from A08_network import GameClient, RunningAvg, setClientColors
             
#=======================================================================
# Functions       
#=======================================================================

def signoff(user_state):
    sys.exit()
    
def checkforUserInput(user_state):
    
    # Get all the events since the last call to get().
    for event in pygame.event.get():
        if (event.type == pygame.QUIT): 
            signoff(user_state)
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                signoff(user_state)
            
            elif (event.key==K_1):            
                return 1           
            elif (event.key==K_2):                          
                return 2
            elif (event.key==K_3):
                return 3   
            
            elif (event.key==K_a):
                user_state['a'] = 'D'
            elif (event.key==K_s):
                user_state['s'] = 'D'
            elif (event.key==K_d):
                user_state['d'] = 'D'
            elif (event.key==K_w):
                user_state['w'] = 'D'
                
        elif (event.type == pygame.KEYUP):
            if (event.key==K_a):
                user_state['a'] = 'U'
            elif (event.key==K_s):
                user_state['s'] = 'U'
            elif (event.key==K_d):
                user_state['d'] = 'U'
            elif (event.key==K_w):
                user_state['w'] = 'U'
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            user_state['mouseB1'] = 'D'
        
        elif event.type == pygame.MOUSEBUTTONUP:
            user_state['mouseB1'] = 'U'

        # cursor x,y
        user_state['mouseXY'] = pygame.mouse.get_pos()

#=======================================================================
# Main program
#=======================================================================

def main():
    pygame.init()

    background_color = THECOLORS["yellow"] 
    client_colors = setClientColors()

    client_display = pygame.display.set_mode((600,400))

    # Instantiate clock to control the framerate.
    client_clock = pygame.time.Clock()

    # background color of the game pad   
    client_display.fill( background_color)

    parser = argparse.ArgumentParser( description='Input client parameters.')
    # Example IP address used here; edit this line.
    parser.add_argument('serverIP', type=str, nargs='?', default="192.168.1.106")
    args = parser.parse_args()
    print("args:", args.serverIP)
                                  
    client = GameClient( host=args.serverIP, port=5000)
    client.connect()
    
    pygame.display.set_caption(f"CLIENT {client.client_name} : send mouse and keyboard state")

    # Initialize user state dictionary.
    user_state = {'ID': client.id, 'mouseXY':(0,0), 'mouseB1':'U',
                  'a':'U', 's':'U', 'd':'U', 'w':'U'}

    framerate_limit = 120
    fr_avg = RunningAvg(100, pygame)

    while True:
        dt_s = float( client_clock.tick( framerate_limit) * 1e-3)
        
        checkforUserInput( user_state)
        
        client.send_state( user_state)
        
        # background
        client_display.fill( background_color)
        
        fr_avg.update( client_clock.get_fps())
        fr_avg.draw( client_display, 150, 50)
        
        if client.running:
            # Small rectangle to illustrate the client color that will appear on the server screen.
            pygame.draw.rect( client_display, client_colors[client.client_name], pygame.Rect(50, 50, 60, 20), 5)
            
        pygame.display.flip()
    
    
if __name__ == "__main__":
    main() 