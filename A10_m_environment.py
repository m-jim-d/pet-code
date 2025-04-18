#!/usr/bin/env python3

# Filename: A10_m_environment.py

"""
Environment management for 2D physics simulations.

This module provides core environment management functionality for the physics simulation,
including coordinate transformations, user input handling, and display management. The main
components are:

Classes:
    Client: Manages client state including cursor position, key states, and selected objects
    GameWindow: Handles the pygame display window, including rendering and text display
    Environment: Core simulation environment managing coordinate systems and user interaction

Key Features:
    - Screen-to-world coordinate transformations with zoom and pan support
    - Multi-client input processing (keyboard, mouse) 
    - Physics timestep control (fixed vs. floating)
    - Network client support with state synchronization
    - FPS and game state display
    - Object selection and manipulation

The environment supports multiple physics engines (circular, perfect-kiss, Box2D) and
provides consistent coordinate transformations and user interaction across all modes.
"""

import sys, math, platform, os

import pygame
# key constants
from pygame.locals import (
    K_ESCAPE,
    K_KP1, K_KP2, K_KP3,
    K_a, K_s, K_d, K_w,
    K_i, K_j, K_k, K_l, K_SPACE,
    K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0,
    K_f, K_g, K_r, K_x, K_e, K_q,
    K_n, K_h, K_LCTRL, K_RCTRL, K_z, K_p,
    K_t, K_LSHIFT, K_RSHIFT, K_F1, K_TAB,
    K_RIGHT, K_LEFT
)
from pygame.color import THECOLORS

from A08_network import RunningAvg, setClientColors
from A09_vec2d import Vec2D
import A10_m_globals as g


def custom_update(self, client_name, state_dict):    
    self.CS_data[client_name].cursor_location_px = state_dict['mXY']  # mouse x,y
    self.CS_data[client_name].buttonIsStillDown = state_dict['mBd']   # mouse button down (true/false)
    self.CS_data[client_name].mouse_button = state_dict['mB']         # mouse button number (1,2,3,0)
    
    self.CS_data[client_name].key_a = state_dict['a']
    self.CS_data[client_name].key_d = state_dict['d']
    self.CS_data[client_name].key_w = state_dict['w']
    
    # Make the s key execute only once per down event.
    # If key is up, make it ready to accept the down ('D') event.
    if (state_dict['s'] == 'U'):
        self.CS_data[client_name].key_s_onoff = 'ON'
        self.CS_data[client_name].key_s = state_dict['s']
    # If getting 'D' from network client and the key is enabled.
    elif (state_dict['s'] == 'D') and (self.CS_data[client_name].key_s_onoff == 'ON'):
        self.CS_data[client_name].key_s = state_dict['s']
    
    self.CS_data[client_name].key_j = state_dict['j']
    self.CS_data[client_name].key_l = state_dict['l']
    self.CS_data[client_name].key_i = state_dict['i']
    self.CS_data[client_name].key_space = state_dict[' ']

    # Make the k key execute only once per down event.
    # If key is up, make it ready to accept the down ('D') event.
    if (state_dict['k'] == 'U'):
        self.CS_data[client_name].key_k_onoff = 'ON'
        self.CS_data[client_name].key_k = state_dict['k']
    # If getting 'D' from network client and the key is enabled.
    elif (state_dict['k'] == 'D') and (self.CS_data[client_name].key_k_onoff == 'ON'):
        self.CS_data[client_name].key_k = state_dict['k']

    self.CS_data[client_name].key_shift = state_dict['lrs']

def signInOut_function(self, client_name, activate=True):
    if activate:
        self.CS_data[client_name].active = True
    else:
        self.CS_data[client_name].active = False
        self.CS_data[client_name].historyXY = []


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
        
        # Freeze it
        self.key_f = "U"
        
        # Zoom
        self.key_n = "U"
        self.key_h = "U"
        self.key_ctrl = "U"
        
        self.key_shift = "U"

        self.key_t = "U"

        # Note that key_e state is not used. However, there is an event (toggle) on K_e
        # for inhibiting screen erasing.
        
        self.selected_puck = None
        
        self.cursor_color = cursor_color
        self.bullet_hit_count = 0
        self.bullet_hit_limit = 50.0
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.1, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}
                                        
    def calc_string_forces_on_pucks_circular(self):
        # Calculated the string forces on the selected puck and add to the aggregate
        # that is stored in the puck object.
        
        # Only check for a selected puck if one isn't already selected. This keeps
        # the puck from unselecting if cursor is dragged off the puck!
        if (self.selected_puck == None):
            if self.buttonIsStillDown:
                self.selected_puck = g.air_table.checkForPuckAtThisPosition(self.cursor_location_px)        
        
        else:
            if not self.buttonIsStillDown:
                # Unselect the puck and bomb out of here.
                self.selected_puck.selected = False
                self.selected_puck = None
                return None
            
            # Use dx difference to calculate the hooks law force being applied by the tether line. 
            # If you release the mouse button after a drag it will fling the puck.
            # This tether force will diminish as the puck gets closer to the mouse point.
            dx_2d_m = g.env.ConvertScreenToWorld(Vec2D(self.cursor_location_px)) - self.selected_puck.pos_2d_m
            
            stringName = "string" + str(self.mouse_button)
            self.selected_puck.cursorString_spring_force_2d_N   += dx_2d_m * self.mouse_strings[stringName]['k_Npm']
            
            # The drag force is generally in the opposite direction from the puck velocity. So the sign term is -1
            # unless the timeDirection has been reversed in testing the reversibility of perfect-kiss collisions. 
            if (g.air_table.engine == 'circular-perfectKiss'):
                sign = -1 * g.air_table.timeDirection 
            else:
                sign = -1
            self.selected_puck.cursorString_puckDrag_force_2d_N += self.selected_puck.vel_2d_mps * sign * self.mouse_strings[stringName]['c_drag']
    
    def calc_string_forces_on_pucks(self):
        self.calc_string_forces_on_pucks_circular()

    def draw_cursor_string(self):
        if (self.selected_puck != None):
            line_points = [g.env.ConvertWorldToScreen(self.selected_puck.pos_2d_m), self.cursor_location_px]

            # small circle at selection point.
            radius_px = 4  # * g.env.viewZoom
            pygame.draw.circle(g.game_window.surface, THECOLORS['red'], line_points[0], radius_px, 2)

            pygame.draw.line(g.game_window.surface, self.cursor_color, line_points[0], line_points[1], 1)  # g.env.zoomLineThickness(1)
                    
    def draw_fancy_server_cursor(self):
        self.draw_server_cursor( self.cursor_color, 0)
        self.draw_server_cursor( THECOLORS["black"], 1)

    def draw_server_cursor(self, color, edge_px):
        cursor_outline_vertices = []
        cursor_outline_vertices.append(  self.cursor_location_px )
        cursor_outline_vertices.append( (self.cursor_location_px[0] + 12,  self.cursor_location_px[1] + 12) )
        cursor_outline_vertices.append( (self.cursor_location_px[0] +  0,  self.cursor_location_px[1] + 17) )
        
        pygame.draw.polygon(g.game_window.surface, color, cursor_outline_vertices, edge_px)

        if self.buttonIsStillDown:
            pygame.draw.circle(g.game_window.surface, THECOLORS['red'], self.cursor_location_px, 4, 2)


class GameWindow:
    def __init__(self, title):
        self.width_px = g.env.screenSize_2d_px.x
        self.height_px = g.env.screenSize_2d_px.y
        
        # The initial World position vector of the Upper Right corner of the screen.
        # Yes, y_px = 0 for UR.
        self.UR_2d_m = g.env.ConvertScreenToWorld(Vec2D(self.width_px, 0))

        self.center_2d_m = Vec2D(self.UR_2d_m.x / 2.0, self.UR_2d_m.y / 2.0)
        
        print(f"Screen dimensions in pixels: {g.env.screenSize_2d_px.x:.0f}, {g.env.screenSize_2d_px.y:.0f}")
        print(f"Screen dimensions in meters: {self.UR_2d_m.x:.2f}, {self.UR_2d_m.y:.2f}")
        print(f"One pixel = {g.env.px_to_m * 1:.4f} meters")
        
        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(g.env.screenSize_2d_px.tuple())

        self.set_caption(title)
        
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()

        # Inhibit the operating-system cursor in the game window.
        pygame.mouse.set_visible(False)

    def set_caption(self, title):
        # Set the caption text without updating the display.
        self.caption = title

    def update_caption(self):
        """Update window caption using multiple methods for better Linux compatibility"""
        # Try standard Pygame method
        pygame.display.set_caption(self.caption)

        if platform.system() == 'Linux':
            try:
                # Try to get the X11 display and window
                if 'DISPLAY' in os.environ:  # Only try X11 if running in X environment
                    import Xlib.display
                    x_display = Xlib.display.Display()
                    x_window = x_display.get_input_focus().focus
                    if x_window:
                        x_window.set_wm_name(self.caption)
                        x_display.sync()
            except ImportError:
                print("Import error. Try this: 'pip install python-xlib'.")
            except Exception:
                pass  # Any other X11 related error

    def update(self):
        pygame.display.update()
        
    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()


class Environment:
    def __init__(self, screen_tuple_px, length_x_m, aspect_ratio_wh):
        self.screenSize_2d_px = Vec2D(screen_tuple_px)
        self.viewOffset_2d_px = Vec2D(0,0)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01
    
        self.px_to_m = length_x_m/float(self.screenSize_2d_px.x)
        self.m_to_px = (float(self.screenSize_2d_px.x)/length_x_m)
        
        self.length_x_m = length_x_m
        self.aspect_ratio_wh = aspect_ratio_wh

        self.client_colors = setClientColors()
                              
        # Initialize the client dictionary with a local (non-network) client.
        self.clients = {'local':Client(THECOLORS["green"])}
        self.clients['local'].active = True
        
        self.fr_avg = RunningAvg(300, pygame, colorScheme='light')
        
        self.constant_dt_s = 1.0/60.0
        self.timestep_fixed = False

        self.tickCount = 0
        self.inhibit_screen_clears = False

        self.dt_render_limit_s = 1.0/120.0
        self.render_timer_s = 0.0

        self.demo_variations = {
            # Regular numeric demos
            0:{'index':0,'count':0},
            1:{'index':0,'count':0},
            2:{'index':0,'count':0},
            3:{'index':0,'count':0},
            4:{'index':0,'count':0},
            5:{'index':0,'count':0},
            6:{'index':0,'count':0},
            7:{'index':0,'count':0},
            8:{'index':0,'count':0},
            9:{'index':0,'count':0},
            # Special perfect kiss demos
            '1p':{'index':0,'count':0},
            '2p':{'index':0,'count':0},
            '3p':{'index':0,'count':0},
        }
                        
    def remove_healthless_pucks(self):
        for puck in g.air_table.pucks[:]:  # [:] indicates a copy 
            if (puck.bullet_hit_count > puck.bullet_hit_limit):
                puck.delete()

    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom
    
    def radians(self, degrees):
        return degrees * math.pi/180.0

    # Convert from pixels to meters
    def m_from_px(self, dx_px):
        return dx_px * self.px_to_m / self.viewZoom
    
    def control_zoom_and_view(self):
        local_user = self.clients['local']
        
        if local_user.key_h == "D" or local_user.key_n == "D":
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
        y_m = (self.screenSize_2d_px.y - point_2d_px.y + self.viewOffset_2d_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D( x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_2d_px.y
        y_px = self.screenSize_2d_px.y - y_px

        # Return a tuple of integers.
        return Vec2D(x_px, y_px, "int").tuple()

    def set_allPucks_elastic(self):
        print("CRs for all pucks have been set for elastic collisions (CR=1)")
        for eachpuck in g.air_table.pucks:
            eachpuck.coef_rest = 1.0
    
    def set_gravity(self, onOff):
        if (onOff == "on"):
            g.air_table.g_ON = True
        else:
            g.air_table.g_ON = False
        self.adjust_restitution_for_gravity()

    def adjust_restitution_for_gravity(self):
        if g.air_table.g_ON:
            g.air_table.g_2d_mps2 = g.air_table.gON_2d_mps2
            for each_puck in g.air_table.pucks:
                if not each_puck.CR_fixed:
                    each_puck.coef_rest = min(each_puck.coef_rest_atBirth, g.air_table.gON_coef_rest_max)
        else:
            g.air_table.g_2d_mps2 = g.air_table.gOFF_2d_mps2
            for each_puck in g.air_table.pucks:
                if not each_puck.CR_fixed:
                    each_puck.coef_rest = 1.0

    def get_local_user_input(self, demo_index):
        local_user = self.clients['local']
        local_user.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()
        
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
                    if local_user.key_shift == 'D':
                        return "1p"
                    else:
                        return 1           
                elif (event.key==K_2):  
                    if local_user.key_shift == 'D':
                        return "2p"
                    else:
                        return 2
                elif (event.key==K_3):
                    if local_user.key_shift == 'D':
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
                    # Stop translational movement.
                    for puck in g.air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0,0)
                    print("all translational speeds set to zero")
                
                elif (event.key==K_r):
                    # Reverse the velocity of all the pucks...
                    for puck in g.air_table.pucks:
                        puck.set_pos_and_vel(puck.pos_2d_m, puck.vel_2d_mps * (-1))
                    print("puck velocities have been reversed")

                elif (event.key==K_g):
                    # Toggle the logical flag for g.
                    g.air_table.g_ON = not g.air_table.g_ON
                    print("g", g.air_table.g_ON)
                    self.adjust_restitution_for_gravity()
                
                elif(event.key==K_x):
                    if local_user.key_shift == 'D':
                        print("Deleting all client pucks.")
                        for puck in g.air_table.pucks[:]:
                            if (puck.client_name):
                                puck.delete()
                    else:
                        print("Deleting the selected puck.")
                        for puck in g.air_table.pucks[:]:
                            if (puck.selected):
                                puck.delete()

                elif (event.key==K_z):
                    print("Perfect Kiss not available in this script.")

                elif (event.key==K_F1):
                    # Toggle FPS display on/off
                    g.air_table.FPS_display = not g.air_table.FPS_display
                
                # Jet keys
                elif (event.key==K_a):
                    local_user.key_a = 'D'

                    if local_user.key_shift == 'D':
                        for puck in g.air_table.pucks[:]:
                            if (puck.selected):
                                print(f"coef rest = {puck.coef_rest}")

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
                elif (event.key==K_LCTRL or event.key==K_RCTRL):
                    local_user.key_ctrl = 'D'
                elif event.key==K_q:
                    print(f"Zooming to 1 and resetting offset ({self.viewZoom},({self.viewOffset_2d_px}))")
                    self.viewOffset_2d_px = Vec2D(0,0)
                    self.viewZoom = 1

                # Toggle penetration correction
                elif ((event.key==K_p) and (local_user.key_ctrl == 'D') and (local_user.key_shift == 'D')):
                    g.air_table.correct_for_puck_penetration = not g.air_table.correct_for_puck_penetration
                    print("Penetration correction is", "ON" if g.air_table.correct_for_puck_penetration else "OFF")
                    
                # Pause the game loop
                elif ((event.key==K_p) and not (local_user.key_shift == 'D')):
                    g.air_table.stop_physics = not g.air_table.stop_physics
                    if (not g.air_table.stop_physics):
                        pygame.mouse.set_visible(False)
                        print("game loop is active again")
                    else:
                        pygame.mouse.set_visible(True)
                        print("game loop is paused")
                
                # Set equal-interval physics (more stability for Jello Madness)
                elif ((event.key==K_p) and (local_user.key_shift == 'D') and (not g.air_table.stop_physics)):
                    self.timestep_fixed = not self.timestep_fixed
                    if self.timestep_fixed:
                        self.constant_dt_s = 1.0/self.fr_avg.result
                        print(f"physics engine is stepping in equal (fixed) intervals of 1/{int(self.fr_avg.result)}")
                    else:
                        print("physics engine steps are FLOATING with the game loop")
                    self.fr_avg.reset()
                
                # Shift modifier
                elif (event.key==K_LSHIFT or event.key==K_RSHIFT):
                    local_user.key_shift = 'D'

                elif (event.key==K_t):
                    local_user.key_t = 'D'
                
                # Handle demo variations
                elif (event.key in [K_RIGHT, K_LEFT]):
                    if g.air_table.engine != 'box2d' and demo_index in [2,3,4]:
                        print("Variations only available in box2d engine mode")
                        return demo_index

                    if self.demo_variations[demo_index]['count'] <= 1:
                        print(f"Demo {demo_index} has no additional variations")
                        return demo_index
                        
                    # Increment or decrement the variation index
                    delta = 1 if event.key == K_RIGHT else -1
                    self.demo_variations[demo_index]['index'] = (
                        self.demo_variations[demo_index]['index'] + delta
                    ) % self.demo_variations[demo_index]['count']
                    
                    print(f"Demo {demo_index} variation {self.demo_variations[demo_index]['index'] + 1} of {self.demo_variations[demo_index]['count']}")
                    return demo_index
                    
                elif ((event.key==K_e) and (local_user.key_shift == 'D')):
                    self.inhibit_screen_clears = not self.inhibit_screen_clears
                    print("inhibit_screen_clears =", self.inhibit_screen_clears)
                
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
                elif (event.key==K_LCTRL or event.key==K_RCTRL):
                    local_user.key_ctrl = 'U'
                    
                # Shift modifier.
                elif (event.key==K_LSHIFT or event.key==K_RSHIFT):
                    local_user.key_shift = 'U'
                
                elif (event.key==K_t):
                    local_user.key_t = 'U'
                    
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
                
            elif ((event.type == pygame.MOUSEMOTION) and (local_user.key_ctrl == 'D')):
                self.viewOffset_2d_px -= Vec2D(event.rel[0], -event.rel[1])
