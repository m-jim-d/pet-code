#!/usr/bin/env python3

# Filename: A10_2D_baseline_server.py

import sys
import pygame
import math
import socket
import platform, subprocess

# PyGame Constants
from pygame.locals import (
    K_ESCAPE,
    K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0,
    K_f, K_g,
    K_n, K_h,
    K_p
)

from pygame.color import THECOLORS

# Import the vector class from a local module (in this same directory)
from A09_vec2d import Vec2D

from A08_network import GameServer, RunningAvg, setClientColors

#=====================================================================
# Classes
#=====================================================================

class Client:
    def __init__(self, cursor_color):
        self.cursor_location_px: tuple[int, int] = (0,0)   # x_px, y_px
        self.mouse_button = 1  # 1, 2, or 3
        self.buttonIsStillDown = False        
        
        self.active = False
        
        # Zoom
        self.key_n = "U"
        self.key_h = "U"
        
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

        
class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, puck_color = THECOLORS["grey"]):
        self.radius_m = radius_m
        self.radius_px = round(env.px_from_m(self.radius_m * env.viewZoom))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = Vec2D(0.0,0.0)
        
        self.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        self.jet_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)

        self.impulse_2d_Ns = Vec2D(0.0,0.0)
        
        self.selected = False
        
        self.color = puck_color

        air_table.pucks.append(self)
        
    # If you print an object instance...
    def __str__(self):
        return f"puck: x is {self.pos_2d_m.x}, y is {self.pos_2d_m.y}"
        
    def draw(self):
        # Convert x,y to pixel screen location and then draw.
        self.pos_2d_px = env.ConvertWorldToScreen( self.pos_2d_m)
        
        # Update based on zoom factor
        self.radius_px = round(env.px_from_m( self.radius_m))
        if (self.radius_px < 3):
            self.radius_px = 3
                    
        puck_circle_thickness = 3
        
        # Draw main puck body.
        pygame.draw.circle( game_window.surface, self.color, self.pos_2d_px, self.radius_px, puck_circle_thickness)
        
            
class Spring:
    def __init__(self, p1, p2, length_m=3.0, strength_Npm=0.5, width_m=0.025, color=THECOLORS["yellow"], 
                       damper_Ns2pm2=0.5):
        self.p1 = p1
        self.p2 = p2
        self.p1p2_separation_2d_m = Vec2D(0,0)
        self.p1p2_separation_m = 0
        self.p1p2_normalized_2d = Vec2D(0,0)
        
        self.length_m = length_m
        self.strength_Npm = strength_Npm
        self.damper_Ns2pm2 = damper_Ns2pm2
        self.unstretched_width_m = width_m #0.05
        
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_px = []
        
        self.color = color
        self.draw_as_line = False
        
        air_table.springs.append(self)
    
    def calc_spring_forces_on_pucks(self):
        self.p1p2_separation_2d_m = self.p1.pos_2d_m - self.p2.pos_2d_m
        
        self.p1p2_separation_m =  self.p1p2_separation_2d_m.length()
        
        self.p1p2_normalized_2d = self.p1p2_separation_2d_m / self.p1p2_separation_m
        
        # Spring force:  acts along the separation vector and is proportional to the separation distance.
        spring_force_on_1_N = self.p1p2_normalized_2d * (self.length_m - self.p1p2_separation_m) * self.strength_Npm
        
        # Damper force:  acts along the separation vector and is proportional to the relative speed.
        v_relative_2d_mps = self.p1.vel_2d_mps - self.p2.vel_2d_mps
        v_relative_alongNormal_2d_mps = v_relative_2d_mps.projection_onto(self.p1p2_normalized_2d)
        damper_force_on_1_N = v_relative_alongNormal_2d_mps * self.damper_Ns2pm2
        
        # Net force by both spring and damper
        SprDamp_force_2d_N = spring_force_on_1_N - damper_force_on_1_N
        
        # This force acts in opposite directions for each of the two pucks. Notice the "+=" here, this
        # is an aggregate across all the springs. This aggregate MUST be reset (zeroed) after the movements are
        # calculated. So by the time you've looped through all the springs, you get the NET force, one each ball, 
        # applied of all individual springs.
        self.p1.SprDamp_force_2d_N += SprDamp_force_2d_N * (+1) 
        self.p2.SprDamp_force_2d_N += SprDamp_force_2d_N * (-1)
            
    def width_to_draw_m(self):
        width_m = self.unstretched_width_m * (1 + 0.30 * (self.length_m - self.p1p2_separation_m))
        if width_m < (0.05 * self.unstretched_width_m):
            self.draw_as_line = True
            width_m = 0.0
        else:
            self.draw_as_line = False
        return width_m
    
    def draw(self):   
        # Change the width to indicate the stretch or compression in the spring. Note, it's good to 
        # do this outside of the main calc loop (using the rendering timer). No need to do all this each
        # time step.
        
        width_m = self.width_to_draw_m()
        
        # Calculate the four corners of the spring rectangle.
        p1p2_perpendicular_2d = self.p1p2_normalized_2d.rotate90()
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_m.append(self.p1.pos_2d_m + (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p1.pos_2d_m - (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p2.pos_2d_m - (p1p2_perpendicular_2d * width_m))
        self.spring_vertices_2d_m.append(self.p2.pos_2d_m + (p1p2_perpendicular_2d * width_m))
        
        # Transform from world to screen.
        self.spring_vertices_2d_px = []
        for vertice_2d_m in self.spring_vertices_2d_m:
            self.spring_vertices_2d_px.append( env.ConvertWorldToScreen( vertice_2d_m))
        
        # Draw the spring
        if self.draw_as_line == True:
            pygame.draw.aaline(game_window.surface, self.color, env.ConvertWorldToScreen(self.p1.pos_2d_m),
                                                                       env.ConvertWorldToScreen(self.p2.pos_2d_m))
        else:
            pygame.draw.polygon(game_window.surface, self.color, self.spring_vertices_2d_px)
        
class AirTable:
    def __init__(self, walls_dic):
        self.gON_mps2 = Vec2D(-0.0, -9.0)
        self.gOFF_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_mps2
        self.g_ON = False
        
        self.pucks = []
        self.springs = []
        self.walls = walls_dic
        self.collision_count = 0
        self.coef_rest_puck =  0.90
        self.coef_rest_table = 0.90

        self.correct_for_wall_penetration = True
        self.correct_for_puck_penetration = True
                             
    def draw(self):
        #{"L_m":0.0, "R_m":10.0, "B_m":0.0, "T_m":10.0}
        topLeft_2d_px =   env.ConvertWorldToScreen( Vec2D( self.walls['L_m'],        self.walls['T_m']))
        topRight_2d_px =  env.ConvertWorldToScreen( Vec2D( self.walls['R_m']-0.01,   self.walls['T_m']))
        botLeft_2d_px =   env.ConvertWorldToScreen( Vec2D( self.walls['L_m'],        self.walls['B_m']+0.01))
        botRight_2d_px =  env.ConvertWorldToScreen( Vec2D( self.walls['R_m']-0.01,   self.walls['B_m']+0.01))
        
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topLeft_2d_px,  topRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], topRight_2d_px, botRight_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botRight_2d_px, botLeft_2d_px,  1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], botLeft_2d_px,  topLeft_2d_px,  1)
    
    def checkForPuckAtThisPosition(self, x_px_or_tuple, y_px = None):
        if y_px == None:
            self.x_px = x_px_or_tuple[0]
            self.y_px = x_px_or_tuple[1]
        else:
            self.x_px = x_px_or_tuple
            self.y_px = y_px
        
        test_position_m = env.ConvertScreenToWorld(Vec2D(self.x_px, self.y_px))
        for puck in self.pucks:
            vector_difference_m = test_position_m - puck.pos_2d_m
            # Use squared lengths for speed (avoid square root)
            mag_of_difference_m2 = vector_difference_m.length_squared()
            if mag_of_difference_m2 < puck.radius_m**2:
                puck.selected = True
                return puck
        return None

    def update_TotalForce_Speed_Position(self, puck, dt_s):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/dt_s)
        
        # Acceleration from Newton's law.
        acc_2d_mps2 = puck_forces_2d_N / puck.mass_kg
        
        # Acceleration changes the velocity:  dv = a * dt
        # Velocity at the end of the timestep.
        puck.vel_2d_mps = puck.vel_2d_mps + (acc_2d_mps2 * dt_s)
        
        # Calculate the new physical puck position using the average velocity.
        # Velocity changes the position:  dx = v * dt
        puck.pos_2d_m = puck.pos_2d_m + (puck.vel_2d_mps * dt_s)
        
        # Now reset the aggregate forces.
        puck.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        puck.impulse_2d_Ns = Vec2D(0.0,0.0)
    
    def check_for_collisions(self):
        for i, puck in enumerate(self.pucks):
            
            # Check top and bottom walls.
            if (((puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]) or ((puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"])):
                
                if self.correct_for_wall_penetration:
                    if (puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]:
                        penetration_y_m = self.walls["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                        puck.pos_2d_m.y += 2 * penetration_y_m
                
                    if (puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"]:
                        penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls["T_m"]
                        puck.pos_2d_m.y -= 2 * penetration_y_m
                
                puck.vel_2d_mps.y *= -1 * self.coef_rest_table
            
            # Check left and right walls.
            if (((puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]) or ((puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"])):
                
                if self.correct_for_wall_penetration:
                    if (puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]:
                        penetration_x_m = self.walls["L_m"] - (puck.pos_2d_m.x - puck.radius_m)
                        puck.pos_2d_m.x += 2 * penetration_x_m
                
                    if (puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"]:
                        penetration_x_m = (puck.pos_2d_m.x + puck.radius_m) - self.walls["R_m"]
                        puck.pos_2d_m.x -= 2 * penetration_x_m
                        
                puck.vel_2d_mps.x *= -1 * self.coef_rest_table
                
            # Collisions with other pucks. 
            for otherpuck in self.pucks[i+1:]:
                
                # Check if the two puck circles are overlapping.
                
                # Parallel to the normal
                puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                # Parallel to the tangent
                tangent_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)
                
                p_to_p_m2 = puck_to_puck_2d_m.length_squared()
                
                # Keep this check fast by avoiding square roots.
                if (p_to_p_m2 < (puck.radius_m + otherpuck.radius_m)**2):
                    self.collision_count += 1
                                        
                    # Use the p_to_p vector (between the two colliding pucks) as projection target for 
                    # normal calculation.
                    
                    # The calculate velocity components along and perpendicular to the normal.
                    puck_normal_2d_mps = puck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    puck_tangent_2d_mps = puck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                    
                    otherpuck_normal_2d_mps = otherpuck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                    otherpuck_tangent_2d_mps = otherpuck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                    
                    relative_normal_vel_2d_mps = otherpuck_normal_2d_mps - puck_normal_2d_mps
                    
                    if self.correct_for_puck_penetration:
                        # Back out a total of 2x of the penetration along the normal. Back-out amounts for each puck is 
                        # based on the velocity of each puck time 2DT where DT is the time of penetration. DT is calculated
                        # from the relative speed and the penetration distance.
                        
                        relative_normal_spd_mps = relative_normal_vel_2d_mps.length()
                        penetration_m = (puck.radius_m + otherpuck.radius_m) - p_to_p_m2**0.5
                        penetration_time_s = penetration_m / relative_normal_spd_mps
                        
                        penetration_time_scaler = 1.0  # This can be useful for testing to amplify and see the correction.
                        
                        # First, reverse the two pucks, to their collision point, along their incoming trajectory paths.
                        puck.pos_2d_m = puck.pos_2d_m - (puck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))
                        otherpuck.pos_2d_m = otherpuck.pos_2d_m - (otherpuck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))
                        
                        # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restitution)
                        # of 1 here to better avoid stickiness.
                        CR_puck = 1
                        puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                                                       
                        # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
                        # This will put the pucks where they should have been at the time of collision detection.
                        puck.pos_2d_m = puck.pos_2d_m + (puck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))
                        otherpuck.pos_2d_m = otherpuck.pos_2d_m + (otherpuck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))
                           
                    # Assign the AFTER velocities (using the actual CR here) to the puck for use in the next frame calculation.
                    CR_puck = self.coef_rest_puck
                    puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                    
                    # Now that we're done using the current values, set them to the newly calculated AFTERs.
                    puck_normal_2d_mps, otherpuck_normal_2d_mps = puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps
                                        
                    # Add the components back together to get total velocity vectors for each puck.
                    puck.vel_2d_mps = puck_normal_2d_mps + puck_tangent_2d_mps
                    otherpuck.vel_2d_mps = otherpuck_normal_2d_mps + otherpuck_tangent_2d_mps
    
    def normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        # For inputs as defined here, this returns the AFTER normal for the first puck in the inputs. So if B
        # is first, it returns the result for the B puck.
        relative_normal_vel_2d_mps = B_normal_BEFORE_2d_mps - A_normal_BEFORE_2d_mps
        return ( ( (relative_normal_vel_2d_mps * (CR_puck * B_mass_kg)) + 
                   (A_normal_BEFORE_2d_mps * A_mass_kg + B_normal_BEFORE_2d_mps * B_mass_kg) ) /
                   (A_mass_kg + B_mass_kg) ) 
    
    def AandB_normal_AFTER_2d_mps(self, A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck):
        A = self.normal_AFTER_2d_mps(A_normal_BEFORE_2d_mps, A_mass_kg, B_normal_BEFORE_2d_mps, B_mass_kg, CR_puck)
        # Make use of the symmetry in the physics to calculate the B normal (put the B data in the first inputs).
        B = self.normal_AFTER_2d_mps(B_normal_BEFORE_2d_mps, B_mass_kg, A_normal_BEFORE_2d_mps, A_mass_kg, CR_puck)
        return A, B
    

class Environment:
    def __init__(self, screenSize_px, length_x_m):
        self.screenSize_px = Vec2D(screenSize_px)
        self.viewOffset_px = Vec2D(0,0)
        self.viewCenter_px = Vec2D(0,0)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01
    
        self.px_to_m = length_x_m/self.screenSize_px.x
        self.m_to_px = self.screenSize_px.x/length_x_m
        
        self.client_colors = setClientColors()
                              
        # Add a local (non-network) client to the client dictionary.
        self.clients = {'local':Client( THECOLORS["green"])}
        
        self.time_s = 0.0
                                  
    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom
    
    # Convert from pixels to meters
        return dx_px * self.px_to_m / self.viewZoom
    
    def control_zoom_and_view(self):
        if self.clients['local'].key_h == "D":
            self.viewZoom += self.viewZoom_rate * self.viewZoom
        if self.clients['local'].key_n == "D":
            self.viewZoom -= self.viewZoom_rate * self.viewZoom
    
    def ConvertScreenToWorld(self, point_2d_px):
        x_m = (                       point_2d_px.x + self.viewOffset_px.x) / (self.m_to_px * self.viewZoom)
        y_m = (self.screenSize_px.y - point_2d_px.y + self.viewOffset_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D( x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        """
        Convert from world to screen coordinates (pixels).
        In the class instance, we store a zoom factor, an offset indicating where
        the view extents start at, and the screen size (in pixels).
        """
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_px.y
        y_px = self.screenSize_px.y - y_px

        # Return a tuple of integers.
        return Vec2D(x_px, y_px, "int").tuple()

    def get_local_user_input(self):
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
                
                elif (event.key==K_f):
                    for puck in air_table.pucks:
                        puck.vel_2d_mps = Vec2D(0,0)
                
                elif (event.key==K_g):
                    if air_table.g_ON:
                        air_table.g_2d_mps2 = air_table.gOFF_mps2
                        air_table.coef_rest_puck =  1.00
                        air_table.coef_rest_table =  1.00
                    else:
                        air_table.g_2d_mps2 = air_table.gON_mps2
                        air_table.coef_rest_puck =  0.90
                        air_table.coef_rest_table =  0.90
                    air_table.g_ON = not air_table.g_ON
                    print("g", air_table.g_ON)
                                    
                # Zoom keys
                elif (event.key==K_n):
                    local_user.key_n = 'D'
                elif (event.key==K_h):
                    local_user.key_h = 'D'
                
                # Penetration (stickiness) correction
                elif (event.key==K_p):
                    air_table.correct_for_puck_penetration = not air_table.correct_for_puck_penetration
                
                else:
                    return "nothing set up for this key"
            
            elif (event.type == pygame.KEYUP):                    
                # Zoom keys
                if (event.key==K_n):
                    local_user.key_n = 'U'
                elif (event.key==K_h):
                    local_user.key_h = 'U'
            
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
                    
        if local_user.buttonIsStillDown:
            # This will select a puck when the puck runs into the cursor of the mouse with it's button still down.
            mouseX, mouseY = pygame.mouse.get_pos()
            local_user.cursor_location_px = (mouseX, mouseY)

        
class GameWindow:
    def __init__(self, screen_tuple_px, title):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]
        
        # The initial World position vector of the Upper Right corner of the screen.
        # Yes, that's right y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld( Vec2D(self.width_px, 0))
        
        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)

        self.update_caption(title)
        
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()
        
    def update_caption(self, title):
        pygame.display.set_caption( title)
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
        
def make_some_pucks( demo):
    game_window.update_caption("Air Table: Demo #" + str(demo)) 
    air_table.coef_rest_puck =  0.90 # reset to default
    air_table.coef_rest_table = 0.90 # reset to default

    if demo == 1:
        #                   , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3) # maybe not.
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3) 
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
        spacing_factor = 2.0
        grid_size = 4,2
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (1,1)):
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3, THECOLORS["orange"])
                else:    
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3)
    
    elif demo == 3:
        spacing_factor = 1.5
        grid_size = 5,3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):                
                if ((j,k) == (2,2)):
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.55, 0.3, THECOLORS["orange"])
                else:    
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.55, 0.3)
    
    elif demo == 4:
        #air_table.gON_mps2 = Vec2D(-0.0, -20.0)
        spacing_factor = 1.0
        grid_size = 9,6   #9,6
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.25, 5.0, THECOLORS["orange"])
                else:
                    Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.25, 5.0)
    
    elif demo == 5:
        Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
    
        spring_strength_Npm2 = 20.0
        spring_length_m = 1.5
        Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, 
               width_m=0.2, color=THECOLORS["gold"])
        
    elif demo == 6:
        air_table.coef_rest_puck = 0.7
        density = 0.9

        # No springs on this one.
        Puck(Vec2D(3.50, 7.00), 0.90, density)

        radius = 0.75
        p1 = Puck(Vec2D(2.00, 3.00), radius, density)
        p2 = Puck(Vec2D(3.50, 4.50), radius, density)
        p3 = Puck(Vec2D(5.00, 3.00), radius, density)
        
        spring_strength_Npm2 = 250
        spring_length_m = 2.5
        spring_width_m = 0.07
        damper_Ns2pm2 = 5.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            damper_Ns2pm2=damper_Ns2pm2, color=THECOLORS["red"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            damper_Ns2pm2=damper_Ns2pm2, color=THECOLORS["tan"])
        Spring(p3, p1, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            damper_Ns2pm2=damper_Ns2pm2, color=THECOLORS["gold"])
    
    else:
        print("Nothing set up for this key.")
        
def custom_update(self, client_name, state_dict):    
    self.CS_data[ client_name].cursor_location_px = state_dict['mXY']  # mouse x,y
    self.CS_data[ client_name].buttonIsStillDown = state_dict['mBd']   # mouse button down (true/false)
    self.CS_data[ client_name].mouse_button = state_dict['mB']         # mouse button number (1,2,3,0)
    
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

    aspect_ratio = 8/7
    window_width_px = 900
    window_height_px = math.ceil(window_width_px / aspect_ratio)
    window_dimensions_px = (window_width_px, window_height_px)

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = AirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})
    air_table.correct_for_wall_penetration = True
    air_table.correct_for_puck_penetration = True
    
    # Add some pucks to the table.
    make_some_pucks( 6)
    
    # For displaying a smoothed framerate.
    fr_avg = RunningAvg(300, pygame, colorScheme='light')
    
    # Limit the framerate, but let it float below this limit.
    framerate_limit = 300
    dt_render_s = 0.0
    dt_render_limit_s = 1.0/120.0     # = 1.0/render_framerate

    for m in range(1,11):
        # Initialize the client list with some clients.
        c_name = 'C' + str(m)
        env.clients[ c_name] = Client( env.client_colors[ c_name])

    # Setup network server.
    if platform.system() == 'Linux':
        local_ip = subprocess.check_output(["hostname", "-I"]).decode().strip()
    else:
        local_ip = socket.gethostbyname(socket.gethostname())
    print("Server IP address:", local_ip)

    server = GameServer(host='0.0.0.0', port=8888, 
                        window_xy_px=window_dimensions_px,
                        update_function=custom_update, clientStates=env.clients, 
                        signInOut_function=signInOut_function)

    while True:
        dt_physics_s = myclock.tick( framerate_limit) * 1e-3
        
        #This check avoids problem when dragging the game window.
        if (dt_physics_s < 0.10):
            
            # Get input from local user.
            demo_index = env.get_local_user_input()
            
            # Reset the game based on local user control.
            if demo_index in [0,1,2,3,4,5,6,7,8,9]:
                print(demo_index)
                # This should remove all references to the pucks and effectively kill them off. If there were other
                # variables referring to these lists, this would not delete the pucks.
                
                # Delete all the objects on the table. Re-initializing these lists (references to the objects in them) effectively
                # deletes the objects.
                air_table.pucks = []
                air_table.springs = []
                
                # Now just black out the screen.
                game_window.clear()
                
                # Reinitialize the demo.
                make_some_pucks( demo_index)               
                        
            if (dt_render_s > dt_render_limit_s):
                # Get input from network clients.
                if server.running:
                    server.accept_clients()
                
            for client_name in env.clients:
                # Calculate client related forces.
                env.clients[client_name].calc_string_forces_on_pucks()
                
            if (dt_render_s > dt_render_limit_s):
                # Control the zoom
                env.control_zoom_and_view()
                                
            # Calculate the forces the springs apply on the pucks...
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                air_table.update_TotalForce_Speed_Position( eachpuck, dt_physics_s)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions()
            
            fr_avg.update( myclock.get_fps())
            
            if (dt_render_s > dt_render_limit_s):
                
                # Erase the blackboard. Change color if stickiness correction is off.
                if air_table.correct_for_puck_penetration:
                    if not air_table.g_ON:
                        game_window.surface.fill((0,0,0))  # black outerspace
                    else:
                        game_window.surface.fill((20,20,70))  # dark blue sky
                else:
                    grey_level = 40
                    game_window.surface.fill((grey_level,grey_level,grey_level))
                              
                # Now draw pucks, springs, mouse tethers...

                fr_avg.draw( game_window.surface, 10, 10)
                
                air_table.draw() # Draw boundaries.
                
                for eachpuck in air_table.pucks: 
                    eachpuck.draw()
                    
                for eachspring in air_table.springs: 
                    eachspring.draw()
                
                for client_name in env.clients:
                    client = env.clients[client_name]
                    client.draw_cursor_string()
                    
                    # Draw cursors for network clients.
                    if ((client_name != 'local') and (client.active)):
                        client.draw_fancy_server_cursor()
                    
                pygame.display.flip()
                dt_render_s = 0
            
            # Limit the rendering framerate to be below that of the physics calculations.
            dt_render_s += dt_physics_s
            
            # Keep track of time for deleting old bullets.
            env.time_s += dt_physics_s

#============================================================
# Run the main program.    
#============================================================
        
main()