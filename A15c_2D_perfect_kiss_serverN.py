#!/usr/bin/env python3

# Filename: A15c_2D_perfect_kiss_serverN.py

import sys
import pygame
import math
from typing import Optional, Union, Tuple
import socket
import random
import platform, subprocess

# PyGame Constants
from pygame.locals import (
    K_ESCAPE,
    K_KP1, K_KP2, K_KP3,
    K_a, K_s, K_d, K_w,
    K_i, K_j, K_k, K_l, K_SPACE,
    K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0,
    K_f, K_g, K_r, K_x, K_e, K_q,
    K_n, K_h, K_LCTRL, K_z,
    K_p
)
from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A08_network import GameServer, RunningAvg, setClientColors
from A15_air_table import PerfectKissAirTable
from A15_air_table_objects import Puck, Spring
import A15_globals

#=====================================================================
# Classes
#=====================================================================

class Client:
    def __init__(self, cursor_color):
        self.cursor_location_px: tuple[int, int] = (0,0)   # x_px, y_px
        self.mouse_button = 1 # 1, 2, or 3
        self.buttonIsStillDown = False
        
        self.active = False
        self.drone = False
        
        # Jet
        self.key_a = "U"
        self.key_s = "U"
        self.key_s_onoff = "ON"
        self.key_d = "U"
        self.key_w = "U"
        
        # Gun
        self.key_j = "U"
        self.key_k = "U"
        self.key_k_onoff = "ON"
        self.key_l = "U"
        self.key_i = "U"
        self.key_space = "U"
        
        # Zoom
        self.key_n = "U"
        self.key_h = "U"
        self.key_lctrl = "U"
        
        self.selected_puck = None
        self.cursor_color = cursor_color
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.2, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}
                                        
    def calc_string_forces_on_pucks(self):
        # Calculated the string forces on the selected puck and add to the aggregate
        # that is stored in the puck object.
        
        # Only check for a selected puck if one isn't already selected. This keeps
        # the puck from unselecting if cursor is dragged off the puck!
        if (self.selected_puck == None):
            if self.buttonIsStillDown:
                self.selected_puck = air_table.checkForPuckAtThisPosition(self.cursor_location_px)        
        
        else:
            if not self.buttonIsStillDown:
                # Unselect the puck and bomb out of here.
                self.selected_puck.selected = False
                self.selected_puck = None
                return None
            
            # Use dx difference to calculate the hooks law force being applied by the tether line. 
            # If you release the mouse button after a drag it will fling the puck.
            # This tether force will diminish as the puck gets closer to the mouse point.
            dx_2d_m = env.ConvertScreenToWorld(Vec2D(self.cursor_location_px)) - self.selected_puck.pos_2d_m
            
            stringName = "string" + str(self.mouse_button)
            self.selected_puck.cursorString_spring_force_2d_N   += dx_2d_m * self.mouse_strings[stringName]['k_Npm']
            self.selected_puck.cursorString_puckDrag_force_2d_N += (self.selected_puck.vel_2d_mps * 
                                                                    -1 * self.mouse_strings[stringName]['c_drag'])
            
    def draw_cursor_string(self):
        if (self.selected_puck != None):
            line_points = [env.ConvertWorldToScreen(self.selected_puck.pos_2d_m), self.cursor_location_px]
            pygame.draw.line(game_window.surface, self.cursor_color, line_points[0], line_points[1], 1)
                    
    def draw_fancy_server_cursor(self):
        self.draw_server_cursor( self.cursor_color, 0)
        self.draw_server_cursor( THECOLORS["black"], 1)

    def draw_server_cursor(self, color, edge_px):
        cursor_outline_vertices = []
        cursor_outline_vertices.append(  self.cursor_location_px )
        cursor_outline_vertices.append( (self.cursor_location_px[0] + 10,  self.cursor_location_px[1] + 10) )
        cursor_outline_vertices.append( (self.cursor_location_px[0] +  0,  self.cursor_location_px[1] + 15) )
        
        pygame.draw.polygon(game_window.surface, color, cursor_outline_vertices, edge_px)


class Environment:
    def __init__(self, screenSize_px, length_x_m):
        self.screenSize_px = Vec2D(screenSize_px)
        
        self.viewOffset_2d_px = Vec2D(0,0)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01
        
        self.px_to_m = length_x_m/float(self.screenSize_px.x)
        self.m_to_px = (float(self.screenSize_px.x)/length_x_m)
        
        self.client_colors = setClientColors()
                              
        # Initialize the client dictionary with a local (non-network) client.
        self.clients = {'local':Client(THECOLORS["green"])}
        self.clients['local'].active = True

        # For displaying a smoothed framerate.
        self.fr_avg = RunningAvg(300, pygame, colorScheme='light')
        
        self.tickCount = 0
        self.inhibit_screen_clears = False
        self.always_render = False
        
        self.dt_render_limit_s = 1.0/120.0
        self.render_timer_s = 0.0
        
    def remove_healthless_pucks(self):
        for puck in air_table.pucks[:]:  # [:] indicates a copy 
            if (puck.bullet_hit_count > puck.bullet_hit_limit):
                puck.delete()
                
    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom
    
    # Convert from pixels to meters
    # Note: still floating values here
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m / self.viewZoom
    
    def control_zoom_and_view(self):
        local_user = self.clients['local']
        if local_user.key_h == "D" or local_user.key_n == "D":
            local_user.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()

            # Cursor world position before changing the zoom. 
            cursor_pos_before_2d_m = self.ConvertScreenToWorld(Vec2D(local_user.cursor_location_px))

            if local_user.key_h == "D":
                self.viewZoom += self.viewZoom_rate * self.viewZoom
            elif local_user.key_n == "D":
                self.viewZoom -= self.viewZoom_rate * self.viewZoom

            # Cursor world position after changing the zoom. 
            cursor_pos_after_2d_m = self.ConvertScreenToWorld(Vec2D(local_user.cursor_location_px))

            # Adjust the view offset to compensate for any change in the cursor's world position.
            # This effectively zooms in and out at the cursor's position.
            change_2d_m = cursor_pos_after_2d_m - cursor_pos_before_2d_m
            change_2d_px = Vec2D(self.px_from_m(change_2d_m.x), self.px_from_m(change_2d_m.y))
            self.viewOffset_2d_px = self.viewOffset_2d_px - change_2d_px
    
    def zoomLineThickness(self, lineThickness_px, noFill=False):
        if (lineThickness_px == 0) and (not noFill):
            # A thickness of zero will fill the shape.
            return 0
        else:
            thickness_px = round( lineThickness_px * self.viewZoom)
            if thickness_px < 1: thickness_px = 1
            return thickness_px

    def ConvertScreenToWorld(self, point_2d_px):
        x_m = (                       point_2d_px.x + self.viewOffset_2d_px.x) / (self.m_to_px * self.viewZoom)
        y_m = (self.screenSize_px.y - point_2d_px.y + self.viewOffset_2d_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D( x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.y
        y_px = self.screenSize_px.y - y_px

        # Return a tuple of integers.
        return Vec2D(x_px, y_px, "int").tuple()
        
    def set_allPucks_elastic(self):
        print("CRs for all pucks have been set for elastic collisions (CR=1)")
        for eachpuck in air_table.pucks:
            eachpuck.coef_rest = 1.0

    # The next two functions give an alternate approach to using a modification key. This could also
    # be done by setting up a user key state for shift and controls keys, and use that to see if
    # the modifier key has been pressed.
    
    def ctrl_key_down(self):
        keys = pygame.key.get_pressed()
        return (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL])
    
    def shift_key_down(self):
        keys = pygame.key.get_pressed()
        return (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        
    def get_local_user_input(self):
        local_user = self.clients['local']
        
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                sys.exit()
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    sys.exit()
                elif (event.key==K_KP1):            
                    return "1p"
                elif (event.key==K_KP2):            
                    return "2p"
                elif (event.key==K_KP3):            
                    return "3p"
                elif (event.key==K_1): 
                    if self.shift_key_down():
                        return "1p"
                    else:
                        return 1           
                elif (event.key==K_2):  
                    if self.shift_key_down():
                        return "2p"
                    else:
                        return 2
                elif (event.key==K_3):
                    if self.shift_key_down():
                        return "3p"
                    else:
                        return 3
                elif (event.key==K_4):
                    return 4
                elif (event.key==K_5):
                    return 5
                elif (event.key==K_6):
                    return 6
                elif (event.key==K_7):
                    return 7
                elif (event.key==K_8):
                    return 8
                elif (event.key==K_9):
                    return 9
                elif (event.key==K_0):
                    return 0
                
                elif (event.key==K_f):
                    for puck in air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0,0)
                    print("all puck speeds set to zero")
                
                elif (event.key==K_r):
                    air_table.count_direction *= -1
                    print("")
                    if self.shift_key_down():
                        air_table.timeDirection *= -1
                        print("time direction has been reversed")
                    else:
                        # Reverse the velocity of all the pucks...
                        for puck in air_table.pucks:
                            puck.vel_2d_mps = puck.vel_2d_mps * (-1)
                        print("puck velocities have been reversed")
                    print("timeDirection =", air_table.timeDirection, "count direction =", air_table.count_direction)
                    
                elif (event.key==K_g):
                    air_table.g_ON = not air_table.g_ON
                    print("g", air_table.g_ON)
                    if air_table.g_ON:
                        air_table.g_2d_mps2 = air_table.gON_2d_mps2
                        air_table.coef_rest = 1.00
                        print("setting puck CRs = 0.85, if not fixed")
                        for eachpuck in air_table.pucks:
                            if not eachpuck.CR_fixed:
                                eachpuck.coef_rest = 0.85
                    else:
                        air_table.g_2d_mps2 = air_table.gOFF_2d_mps2
                        air_table.coef_rest =  1.00
                        print("setting puck CRs = 1.00, if not fixed")
                        for eachpuck in air_table.pucks:
                            if not eachpuck.CR_fixed:
                                eachpuck.coef_rest = 1.00
                
                elif(event.key==K_x):
                    print("Deleting all client pucks.")
                    for puck in air_table.pucks[:]:
                        if (puck.client_name):
                            puck.delete()
                
                elif (event.key==K_z):
                    print("")
                    air_table.perfect_kiss = not air_table.perfect_kiss
                    if (air_table.perfect_kiss):
                        self.set_allPucks_elastic()
                    print("perfect kiss =", air_table.perfect_kiss)
                    
                # Jet keys
                elif (event.key==K_a):
                    local_user.key_a = 'D'
                elif (event.key==K_s):
                    local_user.key_s = 'D'
                elif (event.key==K_d):
                    local_user.key_d = 'D'
                elif (event.key==K_w):
                    local_user.key_w = 'D'
                
                # Gun keys
                elif (event.key==K_j):
                    local_user.key_j = 'D'
                elif (event.key==K_k):
                    local_user.key_k = 'D'
                elif (event.key==K_l):
                    local_user.key_l = 'D'
                elif (event.key==K_i):
                    local_user.key_i = 'D'
                elif (event.key==K_SPACE):
                    local_user.key_space = 'D'
                    
                # Zoom keys
                elif (event.key==K_n):
                    local_user.key_n = 'D'
                elif (event.key==K_h):
                    local_user.key_h = 'D'
                elif (event.key==K_LCTRL):
                    local_user.key_lctrl = 'D'
                elif event.key==K_q:
                    print("Zooming to 1 and resetting offset.")
                    env.viewOffset_2d_px = Vec2D(0,0)
                    env.viewZoom = 1

                elif (event.key==K_p):
                    air_table.stop_physics = not air_table.stop_physics
                    if (not air_table.stop_physics):
                        air_table.game_time_s = 0
                        print("game loop is active again")
                    else:
                        print("game loop is paused")
                        
                elif ((event.key==K_e) and (self.shift_key_down())):
                    env.inhibit_screen_clears = not env.inhibit_screen_clears
                    print("inhibit_screen_clears =", env.inhibit_screen_clears)
                
                else:
                    return "nothing set up for this key"
            
            elif (event.type == pygame.KEYUP):
                # Jet keys
                if   (event.key==K_a):
                    local_user.key_a = 'U'
                elif (event.key==K_s):
                    local_user.key_s = 'U'
                elif (event.key==K_d):
                    local_user.key_d = 'U'
                elif (event.key==K_w):
                    local_user.key_w = 'U'
                
                # Gun keys
                elif (event.key==K_j):
                    local_user.key_j = 'U'
                elif (event.key==K_k):
                    local_user.key_k = 'U'
                elif (event.key==K_l):
                    local_user.key_l = 'U'
                elif (event.key==K_i):
                    local_user.key_i = 'U'
                elif (event.key==K_SPACE):
                    local_user.key_space = 'U'
                    
                # Zoom keys
                elif (event.key==K_n):
                    local_user.key_n = 'U'
                elif (event.key==K_h):
                    local_user.key_h = 'U'
                elif (event.key==K_LCTRL):
                    local_user.key_lctrl = 'U'
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                local_user.buttonIsStillDown = True
            
                (button1, button2, button3) = pygame.mouse.get_pressed()
                if button1:
                    local_user.mouse_button = 1
                elif button2:
                    local_user.mouse_button = 2
                elif button3:
                    local_user.mouse_button = 3
                else:
                    local_user.mouse_button = 0
            
            elif event.type == pygame.MOUSEBUTTONUP:
                local_user.buttonIsStillDown = False
                local_user.mouse_button = 0
                
            elif ((event.type == pygame.MOUSEMOTION) and (local_user.key_lctrl == 'D')):
                self.viewOffset_2d_px -= Vec2D(event.rel[0], -event.rel[1])
                
        if local_user.buttonIsStillDown:
            # This will select a puck when the puck runs into the cursor of the mouse with it's button still down.
            local_user.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()


class GameWindow:
    def __init__(self, screen_tuple_px, title):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]
        
        # The initial World position vector of the Upper Right corner of the screen.
        # Yes, that's right, y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld(Vec2D(self.width_px, 0))
        
        print(f"Screen dimensions in meters: {self.UR_2d_m.x}, {self.UR_2d_m.y}")
        
        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)

        self.update_caption(title)
        
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()
        
    def update_caption(self, title):
        pygame.display.set_caption(title)
        self.caption = title
    
    def update(self):
        pygame.display.update()
        
    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()

#===========================================================
# Functions
#===========================================================
def setup_pool_shot():
    env.always_render = True
    air_table.constant_dt_s = 1/20.0
    
    air_table.inhibit_wall_collisions = True
    env.inhibit_screen_clears = True
    
    # Randomize the starting x position of the incoming puck. Elastic pucks make it reversible.
    Puck(Vec2D(random.random()-0.3, 4.80), 0.45, 0.3, color=THECOLORS["orange"], coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(  25.0, 0.0))
    Puck(Vec2D(4.0,                 4.30), 0.45, 0.3,                            coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(   0.0, 0.0))
       
def make_some_pucks(demo):
    game_window.update_caption("Air-Table Server A15c     Demo #" + str(demo))
    env.fr_avg.reset()
    air_table.coef_rest = 1.00
    env.tickCount = 0
    air_table.time_s = 0.0
    
    env.inhibit_screen_clears = False
    air_table.inhibit_wall_collisions = False
    air_table.correct_for_wall_penetration = True
    air_table.correct_for_puck_penetration = True
    
    air_table.collision_count = 0
    air_table.count_direction = 1

    env.always_render = False
    air_table.constant_dt_s = None
    air_table.perfect_kiss = False
    
    if demo == 1:
        #    position       , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, color=THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3)
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3) 
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
        spacing_factor = 2.0
        grid_size = 4,2
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k)==(1,1)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3, color=puck_color_value)
    
    elif demo == 3:
        spacing_factor = 1.5
        grid_size = 5,3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k)==(2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]

                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.55, 0.3, color=puck_color_value)
    
    elif demo == 4:
        spacing_factor = 1.0
        grid_size = 9,6
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), radius_m=0.25, density_kgpm2=1.0, 
                           color=puck_color_value,
                           CR_fixed=False, coef_rest=0.9)
    
    elif demo == 5:
        Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
        Puck(Vec2D(2.00, 3.00),  0.65, 0.3) 
        Puck(Vec2D(3.50, 4.50),  0.65, 0.3) 
        Puck(Vec2D(5.00, 3.00),  0.65, 0.3) 
        
        # No springs on this one.
        Puck(Vec2D(3.50, 7.00),  0.95, 0.3) 
    
        spring_strength_Npm2 = 200.0 #18.0
        spring_length_m = 2.5
        spring_width_m = 0.07
        Spring(air_table.pucks[0], air_table.pucks[1],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
        Spring(air_table.pucks[1], air_table.pucks[2],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
        Spring(air_table.pucks[2], air_table.pucks[0],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
    
    elif demo == 7:
        air_table.coef_rest = 1.00
        
        # Make user/client controllable pucks for all the active clients.
        y_position_m = 1.0
        
        # Drone clients.
        env.clients["C5"].active = True
        env.clients["C5"].drone = True
        env.clients["C6"].active = True
        env.clients["C6"].drone = True
        
        # Arrange human-controlled pucks in a column.
        for name in env.clients:
            client = env.clients[name]
            if client.active and (not client.drone):
                air_table.buildControlledPuck( x_m=7.0, y_m=y_position_m, r_m=0.45, client_name=name, sf_abs=False)
                y_position_m += 1.3
        
        # Position the drone-controlled pucks in specific locations.      
        air_table.buildControlledPuck( x_m=3.0, y_m=7.0, r_m=0.55, client_name="C5", sf_abs=False)  
        air_table.buildControlledPuck( x_m=3.0, y_m=1.0, r_m=0.55, client_name="C6", sf_abs=False)
        
        # Make some pucks that are not controllable.
        density = 0.7
        
        # Make a horizontal row of pinned-spring pucks.
        for m in range(0, 6): 
            pinPoint_2d = Vec2D(2.0 + (m * 0.65), 4.5)
            tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # Make a vertical column of pinned-spring pucks.
        for m in range(-3, 4):
            pinPoint_2d = Vec2D(2 + 6*0.65, 4.5 + m*0.65)
            tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # One free standing puck
        Puck( Vec2D(9.0, 4.5), 0.7, density, color=THECOLORS["cyan"], hit_limit=20, c_drag=0.7, show_health=True)
                    
    elif demo == 8:
        air_table.game_time_s = 0
        air_table.coef_rest = 1.00
        air_table.buildJelloGrid( angle=(-10,90), speed=(10,40), pos_initial_2d_m=Vec2D(3.0, 1.0))

    elif demo == 9:
        air_table.coef_rest = 1.00
        
        air_table.buildJelloGrid( angle=45, speed=0, pos_initial_2d_m=Vec2D(4.0, 2.5), puck_drag=1.5, show_health=True, coef_rest=0.85)

        env.clients["C5"].active = True
        env.clients["C5"].drone = True
        air_table.buildControlledPuck( x_m=2.0, y_m=8.0, r_m=0.45, client_name="C5")

        env.clients["C6"].active = True
        env.clients["C6"].drone = True
        air_table.buildControlledPuck( x_m=8.5, y_m=1.5, r_m=0.45, client_name="C6")

        # Pin two corners of the jello grid.
        Spring(air_table.pucks[ 1], Vec2D(0.3, 0.3), length_m=0.0, strength_Npm=800.0, width_m=0.02)
        Spring(air_table.pucks[10], Vec2D(9.7, 8.4), length_m=0.0, strength_Npm=800.0, width_m=0.02)
        
    elif demo == '1p':
        air_table.correct_for_puck_penetration = False
        air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '2p':
        air_table.correct_for_puck_penetration = True
        air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '3p':
        air_table.correct_for_puck_penetration = True
        air_table.perfect_kiss = True
        setup_pool_shot()

    else:
        print("Nothing set up for this key.")
        
def display_number(numeric_value, font_object,  mode='textOnBackground'):
    if mode=='textOnBackground':
        # Small background rectangle for the text
        pygame.draw.rect( game_window.surface, THECOLORS["white"], pygame.Rect(10, 10, 35, 20))
        # The text
        txt_string = "%.0f" % numeric_value
        txt_surface = font_object.render( txt_string, True, THECOLORS["black"])
        game_window.surface.blit( txt_surface, [18, 11])
    elif mode=='gameTimer':
        fill = 6
        time_string = f"{numeric_value:{fill}.2f}"
        txt_surface = font_object.render( time_string, True, THECOLORS["white"])
        game_window.surface.blit( txt_surface, [605, 11])
    elif mode=='generalTimer':
        fill = 5
        time_string = f"{numeric_value:{fill}.1f}"
        txt_surface = font_object.render( time_string, True, THECOLORS["white"])
        game_window.surface.blit( txt_surface, [710, 5])
        
def custom_update(self, client_name, state_dict):    
    self.CS_data[ client_name].cursor_location_px = state_dict['mXY']  # mouse x,y
    self.CS_data[ client_name].buttonIsStillDown = state_dict['mBd']   # mouse button down (true/false)
    self.CS_data[ client_name].mouse_button = state_dict['mB']         # mouse button number (1,2,3,0)
    
    self.CS_data[ client_name].key_a = state_dict['a']
    self.CS_data[ client_name].key_d = state_dict['d']
    self.CS_data[ client_name].key_w = state_dict['w']
    
    # Make the s key execute only once per down event.
    # If key is up, make it ready to accept the down ('D') event.
    if (state_dict['s'] == 'U'):
        self.CS_data[ client_name].key_s_onoff = 'ON'
        self.CS_data[ client_name].key_s = state_dict['s']
    # If getting 'D' from network client and the key is enabled.
    elif (state_dict['s'] == 'D') and (self.CS_data[ client_name].key_s_onoff == 'ON'):
        self.CS_data[ client_name].key_s = state_dict['s']
    
    self.CS_data[ client_name].key_j = state_dict['j']
    self.CS_data[ client_name].key_l = state_dict['l']
    self.CS_data[ client_name].key_i = state_dict['i']
    self.CS_data[ client_name].key_space = state_dict[' ']

    # Make the k key execute only once per down event.
    # If key is up, make it ready to accept the down ('D') event.
    if (state_dict['k'] == 'U'):
        self.CS_data[ client_name].key_k_onoff = 'ON'
        self.CS_data[ client_name].key_k = state_dict['k']
    # If getting 'D' from network client and the key is enabled.
    elif (state_dict['k'] == 'D') and (self.CS_data[ client_name].key_k_onoff == 'ON'):
        self.CS_data[ client_name].key_k = state_dict['k']

def signInOut_function(self, client_name, activate=True):
    if activate:
        self.CS_data[client_name].active = True
    else:
        self.CS_data[client_name].active = False
        self.CS_data[client_name].historyXY = []

#============================================================
# Main procedural script.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_table
    
    pygame.init()

    myclock = pygame.time.Clock()

    window_dimensions_px = (800, 700)  # window_width_px, window_height_px

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.
    A15_globals.env = env

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')
    A15_globals.game_window = game_window

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = PerfectKissAirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})
    A15_globals.air_table = air_table
    A15_globals.engine_type = "circular"

    # Extend the clients dictionary to accommodate up to 10 network clients.
    for m in range(1,11):
        c_name = 'C' + str(m)
        env.clients[ c_name] = Client( env.client_colors[ c_name])

    # Font object for rendering text onto display surface.
    fnt_gameTimer = pygame.font.SysFont("Courier", 50)
    fnt_generalTimer = pygame.font.SysFont("Courier", 25)
    pk_collision_cnt = RunningAvg(1, pygame, colorScheme='light')

    # Add some pucks to the table.
    demo_index = 7
    make_some_pucks( demo_index)

    # Setup network server.
    if platform.system() == 'Linux':
        local_ip = subprocess.check_output(["hostname", "-I"]).decode().strip()
    else:
        local_ip = socket.gethostbyname(socket.gethostname())
    print("Server IP address:", local_ip)

    server = GameServer(host='0.0.0.0', port=8888, 
                        update_function=custom_update, clientStates=env.clients, 
                        signInOut_function=signInOut_function)
    
    while True:
        # Limit the framerate, but let it float below this limit.
        if (air_table.constant_dt_s != None):
            gameLoop_FR_limit = int(1.0/air_table.constant_dt_s)
        else:
            gameLoop_FR_limit = 480 # default

        env.tickCount += 1    
        dt_gameLoop_s = float( myclock.tick( gameLoop_FR_limit) * 1e-3)
        
        if (air_table.constant_dt_s != None):
            dt_physics_s = air_table.constant_dt_s
        else:
            dt_physics_s = dt_gameLoop_s
        
        # Get input from local user.
        resetmode = env.get_local_user_input()
        
        # Get input from network clients.
        
        # This dt check avoids problem when dragging the game window.
        if ((dt_physics_s < 0.10) and (not air_table.stop_physics)):
            
            # Reset the game based on local user control.
            if resetmode in ["1p","2p","3p",0,1,2,3,4,5,6,7,8,9]:
                demo_index = resetmode
                print(demo_index)
                
                # This should remove all references to the pucks and effectively delete them. 
                air_table.pucks = []
                air_table.controlled_pucks = []
                air_table.target_pucks = []
                air_table.springs = []
                
                # Now just black out the screen.
                game_window.clear()
                
                # Reinitialize the demo or start a new one.
                make_some_pucks( demo_index)               
                        
            if (env.render_timer_s > env.dt_render_limit_s):
                # Get input from network clients.
                if server.running:
                    server.accept_clients()
                
            if (env.render_timer_s > env.dt_render_limit_s):
                # Control the zoom
                env.control_zoom_and_view()
                
                for controlled_puck in air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    controlled_puck.jet.client_rotation_control()
                    
                    if env.clients[ controlled_puck.client_name].drone:
                        controlled_puck.gun.drone_rotation_control()
                    else:
                        controlled_puck.gun.client_rotation_control()
                    
                    # Turn jet on/off
                    controlled_puck.jet.turn_jet_forces_onoff()

                    # Turn gun on/off
                    controlled_puck.gun.control_firing()
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield()                    
            
            # Calculate forces on the pucks.
            # Cursor strings (spring)
            for client_name in env.clients:
                env.clients[client_name].calc_string_forces_on_pucks()
                
            # Drag on puck movement.
            for eachpuck in air_table.target_pucks:
                eachpuck.calc_regularDragForce()            
            
            # General spring forces.
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                air_table.update_PuckSpeedAndPosition( eachpuck, dt_physics_s * air_table.timeDirection)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions(dt_physics_s * air_table.timeDirection)
            
            if env.tickCount > 10:
                env.fr_avg.update( myclock.get_fps())

            pk_collision_cnt.update( air_table.collision_count)

            if (env.render_timer_s > env.dt_render_limit_s):
                
                # Erase the blackboard.
                if not env.inhibit_screen_clears:
                    if (air_table.perfect_kiss):
                        gray_level = 40
                        game_window.surface.fill((gray_level,gray_level,gray_level))
                    else:
                        if not air_table.g_ON:
                            game_window.surface.fill((0,0,0))  # black
                        else:
                            game_window.surface.fill((20,20,70))  # dark blue
                
                #print(f"{len(air_table.target_pucks)}, {len(air_table.controlled_pucks)}, {len(air_table.pucks)}, s:{len(air_table.springs)}")

                # Clean out old bullets.
                for thisPuck in air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and ((air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        air_table.pucks.remove( thisPuck)
                
                # Display the physics cycle rate.
                env.fr_avg.draw( game_window.surface, 10, 10)
                
                # Display the collision count for the demos where reversibility is well demonstrated. Generally
                # counts up to 100 reverse well.
                if (demo_index in [1,2,3,4]) and (-1000 < pk_collision_cnt.result < 10000) and air_table.perfect_kiss:
                    pk_collision_cnt.draw( game_window.surface, 10, 40, width_px=45, fill=4)
                
                # Display timers.
                if (demo_index == 8):
                    display_number(air_table.game_time_s, fnt_gameTimer, mode='gameTimer')
                elif (air_table.perfect_kiss and demo_index in [1,2,3,4]):
                    display_number(air_table.time_s, fnt_generalTimer, mode='generalTimer')
                
                # Now draw pucks, springs, mouse tethers, and jets.
                # Draw boundaries of table.
                air_table.draw()
                
                for eachpuck in air_table.pucks:
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if eachpuck.jet.client.active:
                            eachpuck.gun.draw_shield()
                            eachpuck.jet.draw()
                            eachpuck.gun.draw()
                            
                for eachspring in air_table.springs: 
                    eachspring.draw()
                
                env.remove_healthless_pucks()
                
                for client_name in env.clients:
                    client = env.clients[client_name]
                    client.draw_cursor_string()
                    
                    # Draw cursors for network clients.
                    if ((client_name != 'local') and client.active and not client.drone):
                        client.draw_fancy_server_cursor()
                    
                pygame.display.flip()
                env.render_timer_s = 0
            
            # Limit the rendering framerate to be below that of the physics calculations.
            env.render_timer_s += dt_physics_s
            
            # Keep track of time for deleting old bullets.
            air_table.time_s += dt_physics_s
            
            # Jello madness game timer
            if air_table.tangled:
                air_table.game_time_s += dt_physics_s
                
#============================================================
# Run the main program.  
#============================================================
        
main()