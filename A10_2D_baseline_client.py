#!/usr/bin/env python3

# Filename: A10_2D_baseline_client.py

import sys, os, time
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

# Argument parsing...
import argparse

from A08_network import GameClient, RunningAvg, setClientColors

#=======================================================================
# Functions       
#=======================================================================

def signoff(client_state):
    sys.exit()
    
def checkforUserInput(client_state):
    
    # Get all the events since the last call to get().
    for event in pygame.event.get():
        if (event.type == pygame.QUIT): 
            signoff(client_state)
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                signoff(client_state)
            
            elif (event.key==K_c):
                mydisplay.fill(THECOLORS["yellow"])  
            
            elif (event.key==K_1):            
                return 1           
            elif (event.key==K_2):                          
                return 2
            elif (event.key==K_3):
                return 3   
            
            elif (event.key==K_a):
                client_state['a'] = 'D'
            elif (event.key==K_s):
                client_state['s'] = 'D'
            elif (event.key==K_d):
                client_state['d'] = 'D'
            elif (event.key==K_w):
                client_state['w'] = 'D'
                
            elif (event.key==K_j):
                client_state['j'] = 'D'
            elif (event.key==K_k):
                client_state['k'] = 'D'
            elif (event.key==K_l):
                client_state['l'] = 'D'
            elif (event.key==K_i):
                client_state['i'] = 'D'
            elif (event.key==K_SPACE):
                client_state[' '] = 'D'
                
            elif (event.key==K_LSHIFT):
                client_state['ls'] = 'D'
            elif (event.key==K_t):
                client_state['t'] = 'D'
            
        elif (event.type == pygame.KEYUP):
            if (event.key==K_a):
                client_state['a'] = 'U'
            elif (event.key==K_s):
                client_state['s'] = 'U'
            elif (event.key==K_d):
                client_state['d'] = 'U'
            elif (event.key==K_w):
                client_state['w'] = 'U'
                
            elif (event.key==K_j):
                client_state['j'] = 'U'
            elif (event.key==K_k):
                client_state['k'] = 'U'
            elif (event.key==K_l):
                client_state['l'] = 'U'
            elif (event.key==K_i):
                client_state['i'] = 'U'
            elif (event.key==K_SPACE):
                client_state[' '] = 'U'
                
            elif (event.key==K_LSHIFT):
                client_state['ls'] = 'U'
            elif (event.key==K_t):
                client_state['t'] = 'U'
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            client_state['mBd'] = True
            
            # Check the button status.
            (button1, button2, button3) = pygame.mouse.get_pressed()
            if button1:
                client_state['mB'] = 1
            elif button2:
                client_state['mB'] = 2
            elif button3:
                client_state['mB'] = 3
            else:
                client_state['mB'] = 0
                
        elif event.type == pygame.MOUSEBUTTONUP:
            client_state['mBd'] = False
            client_state['mB'] = 0

    # cursor x,y
    client_state['mXY'] = pygame.mouse.get_pos()

#=======================================================================
# Main program statements       
#=======================================================================

def main():
    global mydisplay

    # Parse parameters provided in the command line.
    # This description string (and parameter help) gets displayed if help is requested (-h added after the filename).
    parser = argparse.ArgumentParser(description='Please add optional client parameters after the file name. For example: \n' + 
                                                 'A10_2D_baseline_client.py 111.222.22.22')
    # A required positional argument.
    parser.add_argument('serverIP', type=str, help='Use the IP address that is reported by the server when it starts.')
                                    
    args = parser.parse_args()
    print("Server IP Address:", args.serverIP)

    pygame.init()

    mydisplay = pygame.display.set_mode((800, 700))
    client_colors = setClientColors()

    # Clock to control the framerate.
    myclock = pygame.time.Clock()

    client_ID = 0

    client = GameClient( host=args.serverIP, port=5000)
    client.connect()
    
    if client.running and client.client_name is not None:
        pygame.display.set_caption( "Client: " + client.client_name)

    # Initialize client state dictionary.
    client_state = {'ID': client.id,
                    'mXY':(0,0), 'mBd':False, 'mB':1,
                    'a':'U', 's':'U', 'd':'U', 'w':'U', 
                    'j':'U', 'k':'U', 'l':'U', 'i':'U', ' ':'U',
                    'm':'U',
                    'f':'U',
                    't':'U', 'ls':'U'}
        
    framerate_limit = 120
    fr_avg = RunningAvg(100, pygame, colorScheme='light')
    
    flip_timer = 0.0

    while True:
        dt_s = float(myclock.tick(framerate_limit) * 1e-3)
        
        checkforUserInput( client_state)
        
        client.send_state( client_state)
                
        flip_timer += dt_s
        
        fr_avg.update( myclock.get_fps())
        
        if (flip_timer > 0.2):
            # Background
            mydisplay.fill( THECOLORS["black"])
            
            fr_avg.draw( mydisplay, 150, 50)
                        
            if client.running and client.client_name is not None:
                # Small rectangle to illustrate the client color that will be used for the cursor on the server screen.
                pygame.draw.rect( mydisplay, client_colors[ client.client_name], pygame.Rect(50, 50, 60, 20), 5)
            
            pygame.display.flip()
            flip_timer = 0.0
        
#============================================================
# Run the main program.    
#============================================================
        
main()