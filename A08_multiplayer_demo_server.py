#!/usr/bin/env python3

# Filename: A08_multiplayer_demo_server.py

import sys, os
import pygame

# PyGame Constants
from pygame.locals import (
    K_ESCAPE,
    K_c, K_1, K_2, K_3,
    K_a, K_s, K_d, K_w,
    K_j, K_k, K_l, K_i, K_SPACE,
    K_LSHIFT, K_t, K_b, K_y
)
from pygame.color import THECOLORS

from A08_network import GameServer, RunningAvg, setClientColors

import socket


class Client:
    def __init__(self, cursor_color, ID):
        self.cursor_color = cursor_color
        
        self.ID = ID
        
        self.mouseXY = (0,0)   # (x_px, y_px)
        self.mouse_button = 1  # 1, 2, or 3
        
        self.active = False
        
        self.key_w = "U"
        self.key_a = "U"
        self.key_s = "U"
        self.key_d = "U"
        
        self.historyXY = []
        
        self.sendCount = 0

    def draw_cursor(self, color, edge_px=0):
        # An edge_px of 0 indicates the polygon will be filled.
        outline_vertices = []
        outline_vertices.append( self.mouseXY                                  )
        outline_vertices.append( (self.mouseXY[0] + 10,  self.mouseXY[1] + 10) )
        outline_vertices.append( (self.mouseXY[0] +  0,  self.mouseXY[1] + 14) )
        
        pygame.draw.polygon( server_display, color, outline_vertices, edge_px)

    def draw_fancy_cursor(self):
        # First, a filled polygon.
        self.draw_cursor( color=self.cursor_color)
        # The edge_px of 1 indicate no filling and a thin black outline.
        self.draw_cursor( color=THECOLORS["black"], edge_px=1)
                    
    def draw_cursor_history(self):
        for mouse_xy in self.historyXY:
            pygame.draw.circle( server_display, self.cursor_color, mouse_xy, 10, 0)

    def render_keys(self):
        y_offset = 10 + (self.ID - 1) * 37
        
        # The W row...
        pygame.draw.rect(server_display, self.cursor_color, pygame.Rect(10, y_offset, 30, 20))
        pygame.draw.rect(server_display, THECOLORS["black"], pygame.Rect(19, y_offset, 12, 20))
        txt_string = self.key_w
        txt_surface = font_keys.render(txt_string, 1, THECOLORS["yellow"])
        server_display.blit( txt_surface, [20, y_offset])       
        
        # The ASD row...
        pygame.draw.rect(server_display, THECOLORS["black"], pygame.Rect(10, y_offset + 20, 30, 20))
        txt_string = self.key_a + self.key_s + self.key_d
        txt_surface = font_keys.render(txt_string, 1, THECOLORS["yellow"])
        server_display.blit( txt_surface, [11, y_offset + 20])  
            
#=======================================================================
# Functions.        
#=======================================================================
        
def checkforLocalUserInput(): 
    global background_color
    
    # Get all the events since the last call to get().
    for event in pygame.event.get():
        if (event.type == pygame.QUIT): 
            sys.exit()
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                sys.exit()
            elif (event.key==K_c):
                background_color = THECOLORS["cyan"]
            elif (event.key==K_b):
                background_color = THECOLORS["blue"]
            elif (event.key==K_y):
                background_color = THECOLORS["yellow"]
            elif (event.key==K_w):
                background_color = THECOLORS["white"]

def custom_update_example(self, client_name, state_dict):
    # Store current client state
    self.CS_data[client_name].mouseXY = state_dict['mouseXY']
    
    # Add to drawing history if client is drawing
    if state_dict['mouseB1'] == 'D':
        self.CS_data[client_name].historyXY.append(state_dict['mouseXY'])
        # Maintain fixed history length for memory efficiency
        if len(self.CS_data[client_name].historyXY) > 200:
            self.CS_data[client_name].historyXY.pop(0)
    
    self.CS_data[client_name].sendCount += 1
    if self.CS_data[client_name].sendCount > 100:
        print(f"{client_name} at {state_dict['mouseXY']}")
        self.CS_data[client_name].sendCount = 0
        
def signInOut_function(self, client_name, activate=True):
    if activate:
        self.CS_data[client_name].active = True
    else:
        self.CS_data[client_name].active = False
        self.CS_data[client_name].historyXY = []

#=======================================================================
# Main Program
#=======================================================================
        
def main():      

    global clients, client_colors, server_display, font_keys, background_color
        
    pygame.init()

    server_display = pygame.display.set_mode((600,400))
    pygame.display.set_caption("SERVER: render state of all clients")

    # Instantiate clock to help control the framerate.
    server_clock = pygame.time.Clock()
    framerate_limit = 120

    background_color = THECOLORS["yellow"]

    # Font object for rendering text onto display surface.
    font_keys = pygame.font.SysFont("Arial", 16)
    
    # For displaying a smoothed framerate.
    fr_avg = RunningAvg(100, pygame)

    # Setup network server.
    local_ip = socket.gethostbyname(socket.gethostname())
    local_port = 5000
    print("Server IP address and port:", local_ip, local_port)

    client_colors = setClientColors()

    # Initialize clients, a dictionary of client objects.
    clients = {}
    for m in range(1,11):
        c_name = 'C' + str(m)
        clients[ c_name] = Client( client_colors[ c_name], m)
              
    server = GameServer(host='0.0.0.0', port=local_port, 
                        update_function=custom_update_example, clientStates=clients, 
                        signInOut_function=signInOut_function)

    while True:
        dt_s = float( server_clock.tick(framerate_limit) * 1e-3)
        
        if server.running:
            server.accept_clients()
        
        checkforLocalUserInput()
        
        server_display.fill( background_color)
        
        fr_avg.update( server_clock.get_fps())
        fr_avg.draw( server_display, 550, 9)
        
        for clientName in clients:
            client = clients[ clientName]
            if client.active:
                client.render_keys()
                client.draw_cursor_history()
                client.draw_fancy_cursor()
        
        pygame.display.flip()
        
    
if __name__ == "__main__":
    main()    