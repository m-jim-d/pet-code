#!/usr/bin/env python3

# Filename: A16c_2D_B2D_serverN.py

import sys, os
import math
from typing import Optional, Union, Tuple
import socket
import random
import platform, subprocess

import pygame
# key constants
from pygame.locals import (
    K_ESCAPE,
    K_a, K_s, K_d, K_w,
    K_i, K_j, K_k, K_l, K_SPACE,
    K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0,
    K_f, K_g, K_r, K_x, K_e, K_q, K_c,
    K_n, K_h, K_LCTRL, K_z,
    K_p, K_m,
    K_t, K_LSHIFT, K_RSHIFT, K_F1,
    K_RIGHT, K_LEFT
)

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A08_network import GameServer, RunningAvg, setClientColors
from A15_air_table import Box2DAirTable
from A15_air_table_objects import Wall, Puck, Spring
import A15_globals

from Box2D import (b2World, b2Vec2, b2PolygonShape, b2_dynamicBody, b2AABB,
                   b2QueryCallback, b2ContactListener)

# Argument parsing...
import argparse

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
        
        # Freeze it
        self.key_f = "U"
        
        # Zoom
        self.key_n = "U"
        self.key_h = "U"
        self.key_lctrl = 'U'
        
        # Cursor selection modification      #b2d
        self.key_lshift = "U"
        self.key_t = "U"
        
        self.selected_puck = None
        self.COM_selection = None
        self.selection_pointOnPuck_b2d_m = b2Vec2(0,0)  #b2d
        
        self.cursor_color = cursor_color
        self.bullet_hit_count = 0
        self.bullet_hit_limit = 50.0
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.1, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}

        # Special case for objects selected at nonCOM points. c_rot can control the drag (torque)
        # associated with rotation. c_pnt_drag is applied to a selected object at the local body point of the 
        # cursor-selected object. 
        self.mouse_strings_nonCOM = {'string1':{'c_drag':    0.0, 'c_pnt_drag':    2.0, 'c_rot':  0.0, 'k_Npm':     60.0},
                                     'string2':{'c_drag':    0.0, 'c_pnt_drag':    0.1, 'c_rot':  0.0, 'k_Npm':      2.0},
                                     'string3':{'c_drag':    0.0, 'c_pnt_drag':   20.0, 'c_rot':  0.0, 'k_Npm':   1000.0}}
                                        
    def calc_string_forces_on_pucks(self):
        # Calculated the string forces on the selected puck and add to the aggregate
        # that is stored in the puck object.
        
        # First deal with selecting and unselecting.
        # Only check for a selected puck if one isn't already selected. This keeps
        # the puck from unselecting if cursor is dragged off the puck!
        if (self.selected_puck == None):
            if self.buttonIsStillDown:
                # Depending on whether the shift key is down or not, do a COM based selection.
                # Use box2d to look for pucks at the cursor location.
                temp = air_table.checkForPuckAtThisPosition_b2d(self.cursor_location_px)
                self.selected_puck = temp['puck']
                if (self.key_lshift == 'D'):
                    # non-COM selection, specific local point on object.
                    self.selection_pointOnPuck_b2d_m = temp['b2d_xy_m']
                else:
                    # center-of-mass selection
                    self.selection_pointOnPuck_b2d_m = b2Vec2(0,0)
        
        # If a puck is already selected, unselect it if the mouse button is up.
        else:
            if not self.buttonIsStillDown:
                # Unselect the puck and bomb out of here.
                self.selected_puck.selected = False
                self.selected_puck = None
                self.COM_selection = None
                self.selection_2d_m = Vec2D(0,0)
                return None
        
        # Now calculate the forces on a selected puck.
        if (self.selected_puck != None):
            # Calculate the absolute World position of the selection point. Can't just add the local vector to
            # the center of mass vector. Would have to know the orientation (rotation) of the local coordinate system.
            # So use box2d do that transform for us.    #b2d
            
            selection_b2d_m = self.selected_puck.b2d_body.GetWorldPoint( self.selection_pointOnPuck_b2d_m)
            # body.GetWorldVector(localVector)
            self.selection_2d_m = Vec2D( selection_b2d_m.x, selection_b2d_m.y)
            
            # Use dx difference to calculate the hooks law force being applied by the tether line. 
            # If you release the mouse button after a drag it will fling the puck.
            # This tether force will diminish as the puck gets closer to the mouse point.
            
            stringName = "string" + str(self.mouse_button)
            
            # Limit the acceleration caused by the cursor string if the targeted object is very small (light).
            # Do this with a scaling factor based on the mass of the selected object. This avoids instability
            # in the physics engines that can be caused by large changes in position/velocity in a time step.
            if ((self.mouse_strings_nonCOM[stringName]['k_Npm'] / self.selected_puck.mass_kg) > 10000.0):
                cursor_scaling_factor = 3.0 * self.selected_puck.mass_kg
            else:
                cursor_scaling_factor = 1
            
            # Calculation and aggregation of the cursor forces.
            if self.COM_selection:
                # Spring force
                dx_2d_m = env.ConvertScreenToWorld(Vec2D(self.cursor_location_px)) - self.selected_puck.pos_2d_m
                spring_force_2d_N = dx_2d_m * self.mouse_strings[stringName]['k_Npm'] * cursor_scaling_factor
                self.selected_puck.cursorString_spring_force_2d_N += spring_force_2d_N
                
                # Calculate the drag and then add to the pucks aggregate drag force.
                drag_force_2d_N = (self.selected_puck.vel_2d_mps * -1 * self.mouse_strings[stringName]['c_drag']) * cursor_scaling_factor
                self.selected_puck.cursorString_puckDrag_force_2d_N += drag_force_2d_N
                
            else:
                # NonCOM selection:
                # Spring
                dx_2d_m = env.ConvertScreenToWorld(Vec2D(self.cursor_location_px)) - self.selection_2d_m
                
                # Spring force
                spring_force_2d_N = dx_2d_m * self.mouse_strings_nonCOM[stringName]['k_Npm'] * cursor_scaling_factor
                # Append, this force and the location it is to be applied on the body, to the list on the puck.  #b2d
                self.selected_puck.nonCOM_N.append({'force_2d_N': spring_force_2d_N,'local_b2d_m': self.selection_pointOnPuck_b2d_m})
            
                # Calculate a drag force based on the velocity of the selected point. Apply this drag to the selected point on the body.
                v_selected_pnt_b2d_mps = self.selected_puck.b2d_body.GetLinearVelocityFromLocalPoint( self.selection_pointOnPuck_b2d_m)
                #print "vel of selected point:", v_selected_pnt_b2d_mps
                v_selected_pnt_2d_mps = Vec2D(v_selected_pnt_b2d_mps.x, v_selected_pnt_b2d_mps.y)
                point_drag_2d_N = v_selected_pnt_2d_mps * (-1) * self.mouse_strings_nonCOM[stringName]['c_pnt_drag'] * cursor_scaling_factor
                self.selected_puck.nonCOM_N.append({'force_2d_N':point_drag_2d_N, 'local_b2d_m':self.selection_pointOnPuck_b2d_m})
                
                # Calculate a drag force based on COM velocity and then add to the pucks aggregate drag force.
                drag_force_2d_N = (self.selected_puck.vel_2d_mps * -1 * self.mouse_strings_nonCOM[stringName]['c_drag'])* cursor_scaling_factor
                self.selected_puck.cursorString_puckDrag_force_2d_N += drag_force_2d_N

                # Calculate the drag torque...
                torque_force_N = -1 * self.selected_puck.rotation_speed * self.mouse_strings_nonCOM[stringName]['c_rot'] * cursor_scaling_factor
                self.selected_puck.cursorString_torque_force_Nm += torque_force_N
            
            # Some torque to spin the objects.
            if (self.key_t == 'D'):
                if (self.selected_puck.b2d_body.angularVelocity < 200.0):
                    if (self.key_lshift == 'D'):
                        spin_direction = +1.0
                    else:
                        spin_direction = -1.0
                    self.selected_puck.cursorString_torque_force_Nm = 10.0 * self.selected_puck.mass_kg * spin_direction
                    
    def draw_cursor_string(self):
        if (self.selected_puck != None):
            if self.COM_selection:
                selection_location_2d_m = self.selected_puck.pos_2d_m
            else:
                selection_location_2d_m = self.selection_2d_m

            line_points = [env.ConvertWorldToScreen(selection_location_2d_m), self.cursor_location_px]
            pygame.draw.line(game_window.surface, self.cursor_color, line_points[0], line_points[1], 1)
            # Draw small circle at selection point.
            radius_px = 2
            pygame.draw.circle(game_window.surface, THECOLORS["red"], line_points[0], radius_px, 0)
                    
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
        
        self.fr_avg = RunningAvg(300, pygame, colorScheme='light')
        
        self.constant_dt_s = None

        self.tickCount = 0

        self.dt_render_limit_s = 1.0/120.0
        self.render_timer_s = 0.0

        self.demo2_variation_index = 0
        self.demo3_variation_index = 0
                        
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

    # The next two functions give an alternate approach to using a modification key. This could also
    # be done by setting up a user key state for shift and controls keys, and use that to see if
    # the modifier key has been pressed.
    
    def ctrl_key_down(self):
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
            return True
            
    def shift_key_down(self):
        keys = pygame.key.get_pressed()
        if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            return True

    def set_gravity(self, onOff):
        if (onOff == "on"):
            air_table.g_ON = True
        else:
            air_table.g_ON = False
        self.adjust_restitution_for_gravity()

    def adjust_restitution_for_gravity(self):
        if air_table.g_ON:
            air_table.g_2d_mps2 = air_table.gON_2d_mps2
            # Box2d...
            for eachpuck in air_table.pucks:
                if not eachpuck.CR_fixed:
                    eachpuck.b2d_body.fixtures[0].restitution = eachpuck.coef_rest
                if not eachpuck.friction_fixed:
                    eachpuck.b2d_body.fixtures[0].friction = eachpuck.friction
        else:
            air_table.g_2d_mps2 = air_table.gOFF_2d_mps2
            # Box2d...
            for eachpuck in air_table.pucks:
                if not eachpuck.CR_fixed:
                    eachpuck.b2d_body.fixtures[0].restitution = 1.0
                if not eachpuck.friction_fixed:
                    eachpuck.b2d_body.fixtures[0].friction = 0

    def get_local_user_input(self, demo_index):
        local_user = self.clients['local']
        
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                sys.exit()
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    sys.exit()
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
                
                elif (event.key==K_c):
                    # Toggle color option.
                    air_table.color_transfer = not air_table.color_transfer
                    #form['ColorTransfer'].value = air_table.color_transfer
                
                elif (event.key==K_f):
                    # Stop all the pucks...
                    for puck in air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0,0)
                        # And for the Box2d puck.
                        puck.b2d_body.linearVelocity = b2Vec2(0,0)
                
                elif (event.key==K_r):
                    # Stop all the puck rotation...
                    for puck in air_table.pucks:
                        puck.b2d_body.angularVelocity = 0.0
                
                elif (event.key==K_g):
                    # Toggle the logical flag for g.
                    air_table.g_ON = not air_table.g_ON
                    print("g", air_table.g_ON)
                    self.adjust_restitution_for_gravity()
                
                elif (event.key==K_F1):
                    # Toggle FPS display on/off
                    air_table.FPS_display = not air_table.FPS_display
                
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
                    
                # Pause the game loop
                elif ((event.key==K_p) and not self.shift_key_down()):
                    air_table.stop_physics = not air_table.stop_physics
                    if (not air_table.stop_physics):
                        air_table.game_time_s = 0
                        print("game loop is active again")
                    else:
                        print("game loop is paused")
                
                # Set equal-interval physics (more stability for Jello Madness)
                elif ((event.key==K_p) and self.shift_key_down()):
                    if (env.constant_dt_s == None):
                        env.constant_dt_s = 1.0/env.fr_avg.result
                        print(f"physics engine is stepping in equal intervals of 1/{int( env.fr_avg.result)}")
                    else:
                        env.constant_dt_s = None
                        print("physics engine steps are floating with the game loop")
                    env.fr_avg.reset()
                
                # For modifying cursor selection. #b2d
                elif (event.key==K_LSHIFT):
                    local_user.key_lshift = 'D'
                elif (event.key==K_t):
                    local_user.key_t = 'D'
                
                # Increment the variation indices for demos 2 and 3, but keep the main
                # demo index as it is.
                elif (event.key==K_RIGHT):
                    if demo_index == 2:
                        env.demo2_variation_index = (env.demo2_variation_index + 1) % env.d2_state_cnt
                    elif demo_index == 3:
                        env.demo3_variation_index = (env.demo3_variation_index + 1) % env.d3_state_cnt
                    return demo_index
                elif (event.key==K_LEFT):
                    if demo_index == 2:
                        env.demo2_variation_index = (env.demo2_variation_index - 1) % env.d2_state_cnt
                    elif demo_index == 3:
                        env.demo3_variation_index = (env.demo3_variation_index - 1) % env.d3_state_cnt
                    return demo_index
                    
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
                    
                # Cursor selection modification
                #b2d    
                elif (event.key==K_LSHIFT):
                    local_user.key_lshift = 'U'
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
        print(f"One pixel = {env.px_to_m*1} meters")
        
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
        
def make_some_pucks(demo):
    game_window.update_caption("PyBox2D Air-Table Server A16c     Demo #" + str(demo))
    env.constant_dt_s = None

    # This removes all references to pucks and walls and effectively deletes them. 
    for eachpuck in air_table.pucks[:]:
        eachpuck.delete()
    for eachWall in air_table.walls[:]:
        if not eachWall.fence:
            eachWall.delete()

    # Most of the demos don't need the tangle checker.
    air_table.jello_tangle_checking_enabled = False
    
    # Now just black out the screen.
    game_window.clear()

    env.fr_avg.reset()
    env.tickCount = 0

    for client_name in env.clients:
        client = env.clients[client_name]
        if client.drone:
            client.active = False
            client.drone = False

    if demo == 1:
        #    position       , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, color=THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3)
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3) 
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
        initial_states = [
            {"p1": {"rps":   4.0, "color": THECOLORS["white"]},
             "p2": {"rps": -34.0, "color": THECOLORS["darkred"]},
             "p3": {"rps":  30.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":   0.0, "color": THECOLORS["white"]},
             "p2": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p3": {"rps": -15.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":  11.0, "color": THECOLORS["white"]},
             "p2": {"rps":   0.0, "color": THECOLORS["blue"]},
             "p3": {"rps":   0.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":  30.0, "color": THECOLORS["white"]},
             "p2": {"rps":   0.0, "color": THECOLORS["blue"]},
             "p3": {"rps": -30.0, "color": THECOLORS["white"]}},

            {"p1": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p2": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p3": {"rps":   4.0, "color": THECOLORS["darkred"]}}
        ]
        env.d2_state_cnt = len(initial_states)

        state = initial_states[env.demo2_variation_index]
        print("Variation", env.demo2_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"],
              "   p3_rps =", state["p3"]["rps"])
        
        p1 = Puck(Vec2D(2.0, 2.5), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        p1.b2d_body.fixtures[0].friction = 2.0
        
        p2 = Puck(Vec2D(5.0, 7.5), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]
        p2.b2d_body.fixtures[0].friction = 2.0

        p3 = Puck(Vec2D(8.0, 2.5), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p3"]["color"])
        p3.b2d_body.angularVelocity = state["p3"]["rps"]
        p3.b2d_body.fixtures[0].friction = 2.0

        spring_strength_Npm2 = 15.0
        spring_length_m = 1.0
        spring_width_m = 0.10
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p1, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])

        game_window.update_caption( game_window.caption + 
            f"     Variation {env.demo2_variation_index + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f}, {state['p3']['rps']:.1f})"
        )

    elif demo == 3:
        initial_states = [
            {"p1": {"rps":  4.0, "color": THECOLORS["brown"]},
             "p2": {"rps":  2.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  2.0, "color": THECOLORS["tan"]},
             "p2": {"rps": -2.0, "color": THECOLORS["brown"]}},

            {"p1": {"rps":  3.1, "color": THECOLORS["tan"]},
             "p2": {"rps":  3.1, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  0.0, "color": THECOLORS["white"]},
             "p2": {"rps":  2.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  3.0, "color": THECOLORS["white"]},
             "p2": {"rps":  6.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps": -3.1, "color": THECOLORS["tan"]},
             "p2": {"rps": -3.1, "color": THECOLORS["tan"]}}
        ]
        env.d3_state_cnt = len(initial_states)

        state = initial_states[env.demo3_variation_index]
        print("Variation", env.demo3_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"])

        p1 = Puck(Vec2D(2.0, 2.0), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        
        p2 = Puck(Vec2D(8.0, 6.75), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]

        spring_strength_Npm2 = 20.0
        spring_length_m = 1.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.15, c_damp=50.0, color=THECOLORS["yellow"])
    
        game_window.update_caption( game_window.caption + 
            f"     Variation {env.demo3_variation_index + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f})"
        )
    
    elif demo == 4:
        spacing_factor = 1.0
        grid_size = 10,5
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]

                offset_2d_m = Vec2D(0.0, 4.5)
                spacing_factor = 0.7
                position_2d_m = Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)) + offset_2d_m

                Puck(position_2d_m, radius_m=0.25, density_kgpm2=1.0, 
                           color=puck_color_value,
                           CR_fixed=True, coef_rest=0.8, friction=0.05, friction_fixed=True)

        Wall(Vec2D(4.0, 4.5), half_width_m=4.0, half_height_m=0.04, angle_radians=-2*(math.pi/180), border_px=0)
        Wall(Vec2D(7.0, 2.5), half_width_m=3.0, half_height_m=0.04, angle_radians=+2*(math.pi/180), border_px=0)
    
    elif demo == 5:
        Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
        density = 1.5
        radius = 0.7
        
        coef_rest_puck = 0.3
        
        spring_strength_Npm2 = 400.0
        spring_length_m = 2.5
        spring_width_m = 0.07
        spring_drag = 0.0
        spring_damper = 5.0

        Puck(Vec2D(2.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        Puck(Vec2D(3.50, 4.50),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        Puck(Vec2D(5.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        
        # No springs on this one.
        Puck(Vec2D(3.50, 7.00),  0.95, density, coef_rest=coef_rest_puck, CR_fixed=True)
        
        Spring(air_table.pucks[0], air_table.pucks[1],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        Spring(air_table.pucks[1], air_table.pucks[2],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        Spring(air_table.pucks[2], air_table.pucks[0],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        
        # Increase the shock-absorber strength for each spring.
        for spring in air_table.springs:                                 
            spring.damper_Ns2pm2 = spring_damper
                
    elif demo == 7:        
        density = 0.8
        #                              , r_m , density
        tempPuck = Puck(Vec2D(4.0, 1.0), 0.55, density, color=THECOLORS["orange"], show_health=True, hit_limit=10)
        Spring(tempPuck, Vec2D(4.0, 1.0), strength_Npm=300.0, width_m=0.02, c_drag = 1.5)
        
        puck_position = Vec2D(0.0, game_window.UR_2d_m.y) + Vec2D(2.0, -2.0) # starting from upper left
        tempPuck = Puck(puck_position, 1.4, density, rect_fixture=True, aspect_ratio=0.1, show_health=True)
        tempPuck.b2d_body.angularVelocity = 0.5
        Spring(tempPuck, puck_position, strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)

        puck_position = Vec2D(8.5, 4.0)
        tempPuck = Puck(puck_position, 1.4, density, rect_fixture=True, aspect_ratio=0.1, show_health=True)
        tempPuck.b2d_body.angularVelocity = 0.5
        Spring(tempPuck, puck_position, strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)

        # Make some pinned-spring pucks.
        for m in range(0, 6): 
            pinPoint_2d = Vec2D(2.0 + (m * 0.65), 4.0)
            tempPuck = Puck(pinPoint_2d, 0.25, density, color=THECOLORS["orange"], show_health=True, hit_limit=15)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # Make user/client controllable pucks
        # for all the clients.
        y_puck_position_m = 1.0
        for client_name in env.clients:
            client = env.clients[client_name]
            if client.active and not client.drone:
                air_table.buildControlledPuck( x_m=6.4, y_m=y_puck_position_m, r_m=0.45, client_name=client_name, sf_abs=False)
                y_puck_position_m += 1.2
                        
        # drone pucks
        client_name = "C5"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=1.0, y_m=1.0, r_m=0.55, client_name=client_name, sf_abs=False)
        client_name = "C6"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=8.5, y_m=7.0, r_m=0.55, client_name=client_name, sf_abs=False)

        env.set_gravity("off")
            
    elif demo == 8:
        air_table.game_time_s = 0
        air_table.jello_tangle_checking_enabled = True
        air_table.buildJelloGrid( angle=(-10,90), speed=(10,40), pos_initial_2d_m=Vec2D(3.0, 1.0))

    elif demo == 9:
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

        env.set_gravity("off")
    
    elif demo == 0:
        density = 0.7
        width_m = 0.01
        aspect_ratio = 9.0
        x_position_m = 0.3
        for j in range(0, 9):
            y_puck_position_m = (width_m * aspect_ratio) + 0.01
            Puck(Vec2D(x_position_m, y_puck_position_m), width_m, density, rect_fixture=True, aspect_ratio=aspect_ratio)
            width_m *= 1.5
            x_position_m *= 1.5
        # Tilt the first rectangle a bit so when gravity is turned on it starts the chain reaction (dominoes).
        #air_table.pucks[0].b2d_body.angle = -7.0/180.0 * math.pi

        tempPuck = Puck(Vec2D(0.1, 0.2), 0.06, density, rect_fixture=False)
        tempPuck.b2d_body.angularVelocity = -10.0
        
        env.set_gravity("on")

    else:
        print("Nothing set up for this key.")

def display_number(numeric_value, font_object,  mode='FPS'):
    if mode=='FPS':
        fps_value = "%.0f" % numeric_value
        if (env.constant_dt_s != None):
            # Small background rectangle for FPS text (left, top, width, height)
            pygame.draw.rect( game_window.surface, THECOLORS["white"], pygame.Rect(10, 10, 64, 20))
            fps_string = fps_value + " (" + str( int( 1/env.constant_dt_s)) + ")"
        else:
            pygame.draw.rect( game_window.surface, THECOLORS["white"], pygame.Rect(10, 10, 35, 20))
            fps_string = fps_value
        txt_surface = font_object.render( fps_string, True, THECOLORS["black"])
        game_window.surface.blit( txt_surface, [18, 11])
    elif mode=='gameTimer':
        fill = 6
        time_string = f"{numeric_value:{fill}.2f}"
        txt_surface = font_object.render( time_string, True, THECOLORS["white"])
        game_window.surface.blit( txt_surface, [605, 11])
        
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
    air_table = Box2DAirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})
    A15_globals.air_table = air_table
    A15_globals.engine_type = "box2d"

    air_table.buildFence() # walls at the window boundaries.

    # Extend the clients dictionary to accommodate up to 10 network clients.
    for m in range(1,11):
        c_name = 'C' + str(m)
        env.clients[ c_name] = Client( env.client_colors[ c_name])
    
    # Font object for rendering text onto display surface.
    fnt_gameTimer = pygame.font.SysFont("Courier", 50)

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
        if (env.constant_dt_s != None):
            gameLoop_FR_limit = int(1.0/env.constant_dt_s)
        else:
            gameLoop_FR_limit = 480 # default
        
        env.tickCount += 1    
        dt_gameLoop_s = float( myclock.tick( gameLoop_FR_limit) * 1e-3)
        
        if (env.constant_dt_s != None):
            dt_physics_s = env.constant_dt_s
        else:
            dt_physics_s = dt_gameLoop_s
        
        if air_table.FPS_display:
            env.fr_avg.update(1.0/dt_gameLoop_s)
        
        # Get input from local user.
        resetmode = env.get_local_user_input(demo_index)
        
        # This check avoids problem when dragging the game window.
        if ((dt_gameLoop_s < 0.10) and (not air_table.stop_physics)):
            
            # Reset the game based on local user control.
            if resetmode in [0,1,2,3,4,5,6,7,8,9]:
                demo_index = resetmode
                print(demo_index)
                                
                # Start, or restart a demo.
                make_some_pucks( demo_index)               
                        
            if (env.render_timer_s > env.dt_render_limit_s):
                # Get input from network clients.
                if server.running:
                    server.accept_clients()
                
            for client_name in env.clients:
                # Calculate client related forces.
                env.clients[client_name].calc_string_forces_on_pucks()
                
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
                    
                    # Turn gun on/off
                    controlled_puck.gun.control_firing()
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield()
            
            # Calculate jet forces on pucks...
            for controlled_puck in air_table.controlled_pucks:
                controlled_puck.jet.turn_jet_forces_onoff()
            
            # Calculate the forces the springs apply on the pucks...
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                eachpuck.calc_regularDragForce()
                air_table.update_TotalForceVectorOnPuck( eachpuck, dt_physics_s)
            
            # Run Box2d    
            air_table.b2d_world.Step( dt_physics_s, 10, 10)
            
            # Get new positions, translational velocities, and rotational speeds, from box2d
            for eachpuck in air_table.pucks:
                eachpuck.get_Box2d_XandV()
            
            # Check for puck-puck contact.
            if air_table.jello_tangle_checking_enabled:
                air_table.check_for_jello_tangle()

            if env.tickCount > 10:
                env.fr_avg.update( myclock.get_fps())
            
            if (env.render_timer_s > env.dt_render_limit_s):
                
                # Erase the blackboard.
                if not air_table.g_ON:
                    game_window.surface.fill((0,0,0))  # black
                else:
                    game_window.surface.fill((20,20,70))  # dark blue

                #print(f"{len(air_table.target_pucks)}, {len(air_table.controlled_pucks)}, {len(air_table.pucks)}, s:{len(air_table.springs)}")

                # Display the physics cycle rate.
                if air_table.FPS_display:
                    env.fr_avg.draw( game_window.surface, 10, 10)
                    
                if (demo_index == 8):
                    display_number(air_table.game_time_s, fnt_gameTimer, mode='gameTimer')
                
                # Clean out old bullets.
                for thisPuck in air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and ((air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        thisPuck.delete()

                # Draw pucks, springs, mouse tethers, and jets.
                
                for eachWall in air_table.walls:
                    eachWall.draw()

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
            env.render_timer_s += dt_gameLoop_s
            
            # Keep track of time for use in timestamping operations
            # (determine the age of old bullets to be deleted)
            air_table.time_s += dt_gameLoop_s
            
            # Jello madness game timer
            if air_table.jello_tangle_checking_enabled:
                air_table.tangle_checker_time_s += dt_gameLoop_s
                if air_table.tangled:
                    air_table.game_time_s += dt_gameLoop_s
                
#============================================================
# Run the main program.  
#============================================================

if __name__ == "__main__":  
    main()
