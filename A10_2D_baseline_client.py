#!/usr/bin/env python3

# Filename: A10_2D_baseline_client.py

import sys, os, time, platform
import pygame

# PyGame Constants
from pygame.locals import (
    K_ESCAPE,
    K_c, K_1, K_2, K_3,
    K_a, K_s, K_d, K_w,
    K_j, K_k, K_l, K_i, K_SPACE,
    K_LSHIFT, K_RSHIFT, K_t, K_TAB
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
    
def update_client_window():
    global mydisplay
    # Update window dimensions if needed
    if client.window_xy_px != mydisplay.get_size():
        mydisplay = pygame.display.set_mode(client.window_xy_px)
        if client.running:
            print(f"Screen dimensions from server: {client.window_xy_px}")
    
    # Update window caption with Linux compatibility
    if client.running and client.client_name is not None:
        caption = "Client: " + client.client_name
        # Try standard Pygame method
        pygame.display.set_caption(caption)
        
        # Additional Linux-specific window title update
        if platform.system() == 'Linux':
            try:
                # Try to get the X11 display and window
                if 'DISPLAY' in os.environ:  # Only try X11 if running in X environment
                    import Xlib.display
                    x_display = Xlib.display.Display()
                    x_window = x_display.get_input_focus().focus
                    if x_window:
                        x_window.set_wm_name(caption)
                        x_display.sync()
            except ImportError:
                print("Import error. Try this: 'pip install python-xlib'.")
            except Exception:
                pass  # Any other X11 related error

def checkforUserInput(client_state):
    global backGroundColor
    
    # Get all the events since the last call to get().
    for event in pygame.event.get():
        if (event.type == pygame.QUIT): 
            signoff(client_state)
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                signoff(client_state)
            
            elif (event.key==K_c):
                if client_state['lrs'] == 'D':
                    if not client.running:
                        if client.reconnect():
                            update_client_window()
                            # Update client ID in state
                            client_state['ID'] = client.id
                else:
                    if (backGroundColor == THECOLORS["black"]):
                        backGroundColor = THECOLORS["darkslategray"]
                    else:
                        backGroundColor = THECOLORS["black"]
            
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
                
            elif (event.key==K_LSHIFT or event.key==K_RSHIFT):
                client_state['lrs'] = 'D' # left or right shift key

            elif (event.key==K_TAB and (client_state['lrs'] == 'D')):
                if (client_state['socl'] == 'T'):
                    client_state['socl'] = 'F' # select-off-center lock
                else:
                    client_state['socl'] = 'T'
                print("select-off-center lock =", client_state['socl'])

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
                
            elif (event.key==K_LSHIFT or event.key==K_RSHIFT):
                client_state['lrs'] = 'U'

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
    global mydisplay, client, backGroundColor

    # Parse parameters provided in the command line.
    # This description string (and parameter help) gets displayed if help is requested (-h added after the filename).
    parser = argparse.ArgumentParser(description='Please add optional client parameters after the file name. For example: \n' + 
                                                 'A10_2D_baseline_client.py 111.222.22.22')
    # A required positional argument.
    parser.add_argument('serverIP', type=str, help='Use the IP address that is reported by the server when it starts.')
                                    
    args = parser.parse_args()
    print("Server IP Address:", args.serverIP)

    pygame.init()

    client_colors = setClientColors()
    backGroundColor = THECOLORS["black"]

    # Clock to control the framerate.
    myclock = pygame.time.Clock()

    client = GameClient( host=args.serverIP, port=8888)
    client.connect()

    mydisplay = pygame.display.set_mode(client.window_xy_px)
    update_client_window()

    # Initialize client state dictionary.
    client_state = {'ID': client.id,
        'mXY':(0,0), 'mBd':False, 'mB':1,
        'a':'U', 's':'U', 'd':'U', 'w':'U', 
        'j':'U', 'k':'U', 'l':'U', 'i':'U', ' ':'U',
        'm':'U',
        'f':'U',
        't':'U', 
        'lrs':'U', # left/right shift keys 
        'socl':'F' # select-off-center lock
    }
        
    framerate_limit = 120
    fr_avg = RunningAvg(100, pygame, colorScheme='light')
    
    flip_timer = 0.0

    while True:
        dt_s = myclock.tick(framerate_limit) * 1e-3
        
        checkforUserInput( client_state)
        
        client.send_state( client_state)
                
        flip_timer += dt_s
        
        fr_avg.update( myclock.get_fps())
        
        if (flip_timer > 0.2):
            # Background
            mydisplay.fill( backGroundColor)
            
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