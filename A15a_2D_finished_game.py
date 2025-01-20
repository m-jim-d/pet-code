#!/usr/bin/env python3

# Filename: A15a_2D_finished_game.py

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
    K_a, K_s, K_d, K_w,
    K_i, K_j, K_k, K_l, K_SPACE,
    K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9, K_0,
    K_f, K_g, K_x, K_q,
    K_n, K_h, K_LCTRL, K_z,
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

        
class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, vel_2d_mps=Vec2D(0.0,0.0),
                       c_drag=0.0, coef_rest=0.85, CR_fixed=False,
                       hit_limit=50.0, show_health=False,
                       color=THECOLORS["gray"], client_name=None, bullet=False, pin=False):
        self.radius_m = radius_m
        self.radius_px = round(env.px_from_m(self.radius_m * env.viewZoom))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.c_drag = c_drag
        
        self.coef_rest = coef_rest
        # This parameter inhibits the changing of the puck's CR when gravity is toggled on and off.
        self.CR_fixed = CR_fixed
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_mps
        
        self.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        self.jet_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        self.puckDrag_force_2d_N = Vec2D(0.0,0.0)

        self.impulse_2d_Ns = Vec2D(0.0,0.0)
        
        self.selected = False
        
        self.color = color
        
        self.client_name = client_name
        self.jet: Optional[Jet] = None
        self.gun: Optional[Gun] = None
        
        self.hit = False
        self.hitflash_duration_timer_s = 0.0
        # Make the hit flash persist for this number of seconds:
        self.hitflash_duration_timer_limit_s = 0.05
        self.show_health = show_health
        
        # bullet nature
        self.bullet = bullet
        self.birth_time_s = air_table.time_s
        self.age_limit_s = 3.0
        
        # Keep track of health.
        self.bullet_hit_count = 0
        self.bullet_hit_limit = hit_limit

        # Add puck to the lists of pucks, controlled pucks, and target pucks.
        if not pin:
            air_table.pucks.append( self)
            if self.client_name:
                air_table.controlled_pucks.append( self)
            if not self.bullet:
                air_table.target_pucks.append( self)
            
    # If you print an object instance...
    def __str__(self):
        return f"puck: x is {self.pos_2d_m.x}, y is {self.pos_2d_m.y}"
        
    def delete(self):
        for spring in air_table.springs[:]:
            if (spring.p1 == self) or (spring.p2 == self):
                air_table.springs.remove( spring)
        
        if self in air_table.controlled_pucks: 
            air_table.controlled_pucks.remove( self)
           
        if self in air_table.target_pucks:
            air_table.target_pucks.remove( self)
            
        air_table.pucks.remove( self) 
        
    def calc_regularDragForce(self):  
        self.puckDrag_force_2d_N = self.vel_2d_mps * -1 * self.c_drag
        
    def draw(self):
        # Convert x,y to pixel screen location and then draw.
        
        self.pos_2d_px = env.ConvertWorldToScreen( self.pos_2d_m)
        
        # Update based on zoom factor in px_from_m.
        self.radius_px = round(env.px_from_m( self.radius_m))
        if (self.radius_px < 2):
            self.radius_px = 2
            
        # Just after a hit, fill the whole circle with RED (i.e., thickness = 0).
        if self.hit:
            puck_border_thickness = 0
            puck_color = THECOLORS["red"]
            self.hitflash_duration_timer_s += env.dt_render_limit_s
            if self.hitflash_duration_timer_s > self.hitflash_duration_timer_limit_s:
                self.hit = False
        else:
            puck_border_thickness = 3
            puck_color = self.color
        
        # Draw main puck body.
        pygame.draw.circle( game_window.surface, puck_color, self.pos_2d_px, self.radius_px, env.zoomLineThickness(puck_border_thickness))
        
        # Draw life (poor health) indicator circle.
        if (not self.bullet and self.show_health):
            spent_fraction = float(self.bullet_hit_count) / float(self.bullet_hit_limit)
            life_radius = spent_fraction * self.radius_px
            if (life_radius > 2.0):
                life_radius_px = round(life_radius)
            else:
                life_radius_px = 2
            
            pygame.draw.circle(game_window.surface, THECOLORS["red"], self.pos_2d_px, life_radius_px, env.zoomLineThickness(2))

            
class RotatingTube:
    def __init__(self, puck, sf_abs=False):
        # Associate the tube with the puck.
        self.puck = puck
    
        self.color = env.clients[self.puck.client_name].cursor_color
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 360.0
        
        # Scaling factors to manage the aspect ratio of the tube.
        if sf_abs:  # Absolute
            self.sf_x = 0.15
            self.sf_y = 0.50
        else:       # Relative
            self.sf_x = 0.15 * (self.puck.radius_m/0.45)
            self.sf_y = 0.50 * (self.puck.radius_m/0.45)
        
        # Notice the counter-clockwise drawing pattern. Four vertices for a rectangle.
        # Each vertex is represented by a vector.
        self.tube_vertices_2d_m = [Vec2D(-0.50 * self.sf_x, 0.00 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 0.00 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 1.00 * self.sf_y),
                                   Vec2D(-0.50 * self.sf_x, 1.00 * self.sf_y)]
        
        # Define a normal (1 meter) pointing vector to keep track of the direction of the jet.
        self.direction_2d_m: Vec2D = Vec2D(0.0, 1.0)
        
    def rotate_vertices(self, vertices_2d_m, angle_deg):
        for vertex_2d_m in vertices_2d_m:
            vertex_2d_m.rotated( angle_deg, sameVector=True)
    
    def rotate_everything(self, angle_deg):
        # Rotate the pointer.
        self.direction_2d_m.rotated( angle_deg, sameVector=True)
        
        # Rotate the tube.
        self.rotate_vertices( self.tube_vertices_2d_m, angle_deg)
                    
    def convert_from_world_to_screen(self, vertices_2d_m, base_point_2d_m):
        vertices_2d_px = []
        for vertex_2d_m in vertices_2d_m:
            # Calculate absolute position of this vertex.
            vertices_2d_px.append( env.ConvertWorldToScreen(vertex_2d_m + base_point_2d_m))
        return vertices_2d_px
        
    def draw_tube(self, line_thickness=3):
        # Draw the tube on the game-window surface. Establish the base_point as the center of the puck.
        pygame.draw.polygon(game_window.surface, self.color, 
                            self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.puck.pos_2d_m), env.zoomLineThickness(line_thickness))


class Jet( RotatingTube):
    def __init__(self, puck, sf_abs=True):
        # Associate the jet with the puck (referenced in the RotatingTube class).
        super().__init__(puck, sf_abs=sf_abs)
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 360.0
        
        self.color = THECOLORS["yellow4"]
        
        # The jet flame (triangle)
        self.flame_vertices_2d_m =[Vec2D(-0.50 * self.sf_x, 1.02 * self.sf_y), 
                                   Vec2D( 0.50 * self.sf_x, 1.02 * self.sf_y), 
                                   Vec2D(-0.00 * self.sf_x, 1.80 * self.sf_y)]
                                   
        # The nose (triangle)
        self.nose_vertices_2d_m =[Vec2D(-0.50 * self.sf_x, -1.02 * self.sf_y), 
                                  Vec2D( 0.50 * self.sf_x, -1.02 * self.sf_y), 
                                  Vec2D(-0.00 * self.sf_x, -1.40 * self.sf_y)]
                                   
        # Scaler magnitude of jet force.
        self.jet_force_N = 1.3 * self.puck.mass_kg * abs(air_table.gON_2d_mps2.y)
        
        # Point everything down for starters.
        self.rotate_everything( 180)
        
        self.client = env.clients[self.puck.client_name]
        
    def turn_jet_forces_onoff(self):
        if (self.client.key_w == "D"):
            # Force on puck is in the opposite direction of the jet tube.
            self.puck.jet_force_2d_N = self.direction_2d_m * (-1) * self.jet_force_N
        else:    
            self.puck.jet_force_2d_N = self.direction_2d_m * 0.0
            
    def client_rotation_control(self):
        if (self.client.key_a == "D"):
            self.rotate_everything( +1 * self.rotation_rate_dps * env.dt_render_limit_s)
        if (self.client.key_d == "D"):
            self.rotate_everything( -1 * self.rotation_rate_dps * env.dt_render_limit_s)
        if (self.client.key_s == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_jet_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_jet_angle)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the
            # direction once but not keep flipping.
            # This first line is enough to keep the local client from flipping again because
            # the local keyboard doesn't keep sending the "D" event if the key is held down.
            self.client.key_s = "U"
            # This second one is also needed for the network clients because they keep
            # sending the "D" until they release the key.
            self.client.key_s_onoff = "OFF"
    
    def rotate_everything(self, angle_deg):
        # Rotate the pointer.
        self.direction_2d_m.rotated( angle_deg, sameVector=True)
        
        # Rotate the tube.
        self.rotate_vertices( self.tube_vertices_2d_m, angle_deg)
        
        # Rotate the nose.
        self.rotate_vertices( self.nose_vertices_2d_m, angle_deg)
        
        # Rotate the flame.
        self.rotate_vertices( self.flame_vertices_2d_m, angle_deg)

    def draw(self):
        if self.client.drone: return
        
        # Draw the jet tube.        
        self.draw_tube(line_thickness=0)
        
        # Draw a little nose cone on the other side of the puck from the jet. This is a visual aid
        # to help the player see the direction the puck will go when the jet is on.
        pygame.draw.polygon(game_window.surface, THECOLORS["yellow1"], 
                            self.convert_from_world_to_screen(self.nose_vertices_2d_m, self.puck.pos_2d_m), 0)
        
        # Draw the red flame.
        if (self.client.key_w == "D"):
            pygame.draw.polygon(game_window.surface, THECOLORS["red"], 
                                self.convert_from_world_to_screen(self.flame_vertices_2d_m, self.puck.pos_2d_m), 0)
                                
    
class Gun( RotatingTube):
    def __init__(self, puck, sf_abs=True):
        # Associate the gun with the puck (referenced in the RotatingTube class).
        super().__init__(puck, sf_abs=sf_abs)
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 180.0
        
        self.color = env.clients[self.puck.client_name].cursor_color
        
        # Run this method of the RotationTube class to set the initial angle of each new gun.
        self.rotate_everything( 45)
        
        self.bullet_speed_mps = 5.0
        self.fire_time_s = air_table.time_s
        self.firing_delay_s = 0.1
        self.bullet_count = 0
        self.bullet_count_limit = 10
        self.gun_recharge_wait_s = 2.5
        self.gun_recharge_start_time_s = air_table.time_s
        self.gun_recharging = False
        
        self.shield = False
        self.shield_hit = False
        self.shield_hit_duration_s = 0.0
        # Make the hit remove the shield for this number of seconds:
        self.shield_hit_duration_limit_s = 0.05        
        self.shield_hit_count = 0
        self.shield_hit_count_limit = 20
        self.shield_recharging = False
        self.shield_recharge_wait_s = 4.0
        self.shield_recharge_start_time_s = air_table.time_s
        self.shield_thickness = 5
        self.targetPuck = None
        self.client = env.clients[self.puck.client_name]
        
    def client_rotation_control(self):
        if (self.client.key_j == "D"):
            self.rotate_everything( +self.rotation_rate_dps * env.dt_render_limit_s)
        if (self.client.key_l == "D"):
            self.rotate_everything( -self.rotation_rate_dps * env.dt_render_limit_s)
        if (self.client.key_k == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_gun_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_gun_angle)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the
            # direction once but not keep flipping.
            # This first line is enough to keep the local client from flipping again because
            # the local keyboard doesn't keep sending the "D" event if the key is held down.
            self.client.key_k = "U"
            # This second one is also needed for the network clients because they keep
            # sending the "D" until they release the key.
            self.client.key_k_onoff = "OFF"

    def drone_rotation_control(self):
        if self.targetPuck:
            vectorToTarget = self.targetPuck.pos_2d_m - self.puck.pos_2d_m 
            angle_change = vectorToTarget.get_angle() - self.direction_2d_m.get_angle()
            self.rotate_everything( angle_change + 1.0)
        
    def findNewTarget(self):
        puck_indexes = list( range( len( air_table.target_pucks)))
        # Shuffle them.
        random.shuffle( puck_indexes)
        
        for puck_index in puck_indexes:
            puck = air_table.target_pucks[ puck_index]
            # Other than itself, pick a new target.
            if (puck != self.puck) and (puck != self.targetPuck):
                self.targetPuck = puck
                break
        
    def control_firing(self):
        droneShooting = self.client.drone and (len(air_table.target_pucks) > 1)
        
        # Fire only if the shield is off.
        if ((self.client.key_i == "D") and (not self.shield)) or droneShooting:
            # Fire the gun.
            if ((air_table.time_s - self.fire_time_s) > self.firing_delay_s) and (not self.gun_recharging):
                self.fire_gun()
                self.bullet_count += 1
                # Timestamp the firing event.
                self.fire_time_s = air_table.time_s
    
        # Check to see if gun bullet count indicates the need to start recharging.
        if (self.bullet_count > self.bullet_count_limit):
            self.gun_recharge_start_time_s = air_table.time_s
            self.gun_recharging = True
            self.bullet_count = 0
            # At the beginning of the charging period, find a new target. This gives a human player an indication
            # of what the drone is targeting. And since this is at the beginning of the gun charging period, it gives
            # the player some time for evasive maneuvers.
            if self.client.drone:
                self.findNewTarget()
    
        # If recharged.
        if (self.gun_recharging and (air_table.time_s - self.gun_recharge_start_time_s) > self.gun_recharge_wait_s):
            self.gun_recharging = False
            # If the puck the drone is aiming at has been destroyed, find a new target before starting to shoot.
            if self.client.drone and not (self.targetPuck in air_table.target_pucks):
                self.findNewTarget()
                
    def fire_gun(self):
        bullet_radius_m = 0.05
        # Set the initial position of the bullet so that it clears (doesn't collide with) the host puck.
        initial_position_2d_m = (self.puck.pos_2d_m +
                                (self.direction_2d_m * (1.1 * self.puck.radius_m + 1.1 * bullet_radius_m)) )
        temp_bullet = Puck(initial_position_2d_m,  bullet_radius_m, 0.3, bullet=True)
        
        # Relative velocity of the bullet: the bullet velocity as seen from the host puck. This is the
        # speed of the bullet relative to the motion of the host puck (host velocity BEFORE the firing of 
        # the bullet).
        bullet_relative_vel_2d_mps = self.direction_2d_m * self.bullet_speed_mps
        
        # Absolute velocity of the bullet.
        temp_bullet.vel_2d_mps = self.puck.vel_2d_mps + bullet_relative_vel_2d_mps
        
        temp_bullet.color = self.client.cursor_color
        temp_bullet.client_name = self.puck.client_name
                
        # Calculate the recoil impulse from firing the gun (opposite the direction of the bullet).
        self.puck.impulse_2d_Ns = bullet_relative_vel_2d_mps * temp_bullet.mass_kg * (-1)
    
    def control_shield(self):
        if (self.client.key_space == "D") and (not self.shield_recharging):
            self.shield = True
        else:
            self.shield = False
        
        # Check to see if the shield hit count indicates the need to start recharging.
        if self.shield_hit_count > self.shield_hit_count_limit:
            self.shield_recharge_start_time_s = air_table.time_s
            self.shield = False
            self.shield_recharging = True
            self.shield_hit_count = 0
        else:
            self.shield_thickness = env.zoomLineThickness(5 * (1 - self.shield_hit_count/self.shield_hit_count_limit), noFill=True)
        
        # If recharged.
        if (self.shield_recharging and (air_table.time_s - self.shield_recharge_start_time_s) > self.shield_recharge_wait_s):
            self.shield_recharging = False
    
    def draw(self):
        # Draw the gun tube.
        if (self.gun_recharging):
            line_thickness = 3
        else:
            # Fill in the gun tube.
            line_thickness = 0
        
        # Draw the jet tube.
        self.draw_tube( line_thickness)
        
    def draw_shield(self):
        if (self.shield):
            if self.shield_hit:
                # Don't draw the shield for a moment after the hit. This visualizes the shield hit.
                self.shield_hit_duration_s += env.dt_render_limit_s
                if (self.shield_hit_duration_s > self.shield_hit_duration_limit_s):
                    self.shield_hit = False
                    
            else:
                # Display the shield 5px outside of the puck.
                shield_radius_px = self.puck.radius_px + round(5 * env.viewZoom)
                pygame.draw.circle(game_window.surface, self.color, 
                                   self.puck.pos_2d_px, shield_radius_px, self.shield_thickness)
                                   
                                   
class Spring:
    def __init__(self, p1, p2, length_m=3.0, strength_Npm=0.5, color=THECOLORS["yellow"], width_m=0.025, c_damp=0.5, c_drag=0.0):
        
        # Optionally this spring can have one end pinned to a vector point. Do this by passing in p2 as a vector.
        if (p2.__class__.__name__ == 'Vec2D'):
            # Create a point puck at the pinning location.
            # The location of this point puck will never change because
            # it is not in the pucks list that is processed by the
            # physics engine.
            p2 = Puck( p2, 1.0, 1.0, pin=True)
            p2.vel_2d_mps = Vec2D(0.0,0.0)
            length_m = 0.0
        
        self.p1 = p1
        self.p2 = p2
        self.p1p2_separation_2d_m = Vec2D(0,0)
        self.p1p2_separation_m = 0
        self.p1p2_normalized_2d = Vec2D(0,0)
        
        self.length_m = length_m
        self.strength_Npm = strength_Npm
        self.damper_Ns2pm2 = c_damp # 5.0 0.05 0.15
        self.unstretched_width_m = width_m # 0.05
        
        self.c_drag = c_drag
        
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_px = []
        
        self.color = color
        self.draw_as_line = False
        
        # Automatically add this spring to the air_table springs list
        air_table.springs.append(self)
    
    def calc_spring_forces_on_pucks(self):
        self.p1p2_separation_2d_m = self.p1.pos_2d_m - self.p2.pos_2d_m
        
        self.p1p2_separation_m =  self.p1p2_separation_2d_m.length()
        
        # The pinned case needs to be able to handle the zero length spring. The 
        # separation distance will be zero when the pinned spring is at rest.
        # This will cause a divide by zero error if not handled here.
        if ((self.p1p2_separation_m == 0.0) and (self.length_m == 0.0)):
            spring_force_on_1_2d_N = Vec2D(0.0,0.0)
        else:
            self.p1p2_normalized_2d = self.p1p2_separation_2d_m / self.p1p2_separation_m
            
            # Spring force:  acts along the separation vector and is proportional to the separation distance.
            spring_force_on_1_2d_N = self.p1p2_normalized_2d * (self.length_m - self.p1p2_separation_m) * self.strength_Npm
        
        # Damper force: acts along the separation vector and is proportional to the relative speed.
        v_relative_2d_mps = self.p1.vel_2d_mps - self.p2.vel_2d_mps
        v_relative_alongNormal_2d_mps = v_relative_2d_mps.projection_onto(self.p1p2_separation_2d_m)
        damper_force_on_1_N = v_relative_alongNormal_2d_mps * self.damper_Ns2pm2
        
        # Net force by both spring and damper
        SprDamp_force_2d_N = spring_force_on_1_2d_N - damper_force_on_1_N
        
        # This force acts in opposite directions for each of the two pucks. Notice the "+=" here, this
        # is an aggregate across all the springs. This aggregate MUST be reset (zeroed) after the movements are
        # calculated. So by the time you've looped through all the springs, you get the NET force, on each puck,
        # applied by all the individual springs.
        self.p1.SprDamp_force_2d_N += SprDamp_force_2d_N * (+1)
        self.p2.SprDamp_force_2d_N += SprDamp_force_2d_N * (-1)
        
        # Add in some drag forces if a non-zero drag coef is specified. These are based on the
        # velocity of the pucks (not relative speed as is the case above for damper forces).
        self.p1.SprDamp_force_2d_N += self.p1.vel_2d_mps * (-1) * self.c_drag
        self.p2.SprDamp_force_2d_N += self.p2.vel_2d_mps * (-1) * self.c_drag
        
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
        self.gON_2d_mps2 = Vec2D(-0.0, -9.8)
        self.gOFF_2d_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_2d_mps2
        self.g_ON = False
        
        self.controlled_pucks = []
        self.target_pucks = []
        self.pucks = []
        
        self.springs = []
        
        self.walls = walls_dic
        self.collision_count = 0
        self.coef_rest = 1.0

        self.stop_physics = False
        self.tangled = False
        
        self.inhibit_wall_collisions = False
        self.correct_for_wall_penetration = True
        self.correct_for_puck_penetration = True
        
        # General clock time for determining bullet age.
        self.time_s = 0.0
        # Timer for the Jello Madness game.
        self.game_time_s = 0.0
          
    def buildControlledPuck(self, x_m=1.0, y_m=1.0, r_m=0.45, density=0.7, c_drag=0.7, client_name=None, sf_abs=True):
        tempPuck = Puck( Vec2D( x_m, y_m), r_m, density, c_drag=c_drag, 
                         client_name=client_name, show_health=True)
        
        # Let the puck reference the jet and the jet reference the puck.
        tempPuck.jet = Jet( tempPuck, sf_abs=sf_abs)
        # Same with the gun.
        tempPuck.gun = Gun( tempPuck, sf_abs=sf_abs)
        
    def buildJelloGrid(self, angle: Union[int, Tuple[int, int]] = 0, 
                             pos_initial_2d_m: Vec2D = Vec2D(2.5, 1.0),
                             grid_x_n: int = 4, grid_y_n: int = 3,
                             speed: Union[int, Tuple[int, int]] = 0, 
                             puck_drag: float = 0.2,
                             coef_rest: float = 0.3,
                             show_health: bool = False):

        if type(angle) is tuple:                           
            angleOfGrid = random.uniform( angle[0], angle[1])
        else:
            angleOfGrid = angle

        # pos_x_delta_2d_m and pos_y_delta_2d_m are the vectors that take
        # us from one column of pucks to the next and from one puck to the
        # next in a column, respectively. They are rotated by the angleOfGrid
        # so that we can create a grid of pucks at an angle relative to the
        # table.
        pos_x_delta_2d_m = Vec2D(1.2, 0.0)
        pos_x_delta_2d_m.rotated( angleOfGrid, sameVector=True)
        pos_y_delta_2d_m = Vec2D(0.0, 1.2)
        pos_y_delta_2d_m.rotated( angleOfGrid, sameVector=True)

        pos_2d_m = pos_initial_2d_m

        spacing_factor = 1.2 # same as spring length

        # Create a grid of pucks. Starting at the initial position, populate a column of pucks, increasing the y position.
        # Then reset the y position and increase the x position, adding additional columns. k ranges over each puck in a column.
        # j ranges over the columns.

        for j in range(grid_x_n):
            for k in range(grid_y_n):
                #print(f"j,k=({j},{k}) pos_2d_m=({pos_2d_m.x:.2f},{pos_2d_m.y:.2f})")
                # corners
                if ((j,k)==(0,0) or (j,k)==(grid_x_n-1,0) or (j,k)==(0,grid_y_n-1) or (j,k)==(grid_x_n-1,grid_y_n-1)):
                    color=THECOLORS["red"]
                # edges
                elif (j==0) or (j==grid_x_n-1) or (k==0) or (k==grid_y_n-1):
                    color=THECOLORS["orange"]
                # center
                else:
                    color=THECOLORS["gray"]

                Puck( pos_2d_m, 0.25, 5.0, color=color,
                      c_drag=puck_drag, 
                      show_health=show_health, hit_limit=10,
                      coef_rest=coef_rest, CR_fixed=True)
                pos_2d_m = pos_2d_m + pos_y_delta_2d_m
            
            pos_2d_m = pos_2d_m - (pos_y_delta_2d_m * grid_y_n) # Reset the y position for the next column
            pos_2d_m = pos_2d_m + pos_x_delta_2d_m
            

        spring_strength_Npm2 = 800.0
        spring_length_m = 1.2
        spring_damping = 10

        # Springs on pucks in same y position, next to each other in x position.
        for m in range(grid_y_n * (grid_x_n-1)):
            Spring( self.pucks[m], self.pucks[m+grid_y_n], spring_length_m, spring_strength_Npm2, 
                    color=THECOLORS["blue"], c_damp=spring_damping)
        
        # Springs on pucks in same x position, next to each other in y position.
        for m in range(grid_x_n):
            for n in range(grid_y_n-1):
                o_index = n + (m * (grid_y_n))
                #print(f"m:{m}, n:{n}, o_index:{o_index},{o_index+1}")
                Spring( self.pucks[o_index], self.pucks[o_index+1], spring_length_m, spring_strength_Npm2, 
                        color=THECOLORS["blue"], c_damp=spring_damping)
        
        # Springs connected on diagonals (springs are longer).
        spring_length_m = 1.2 * 2**0.5

        for m in range(0,grid_x_n-1):
            for n in range(1,grid_y_n):
                o_index = n + (m * (grid_y_n))
                #print(f"m:{m}, n:{n}, o_index:{o_index},{o_index+(grid_y_n-1)}")
                # Connect to a nearby puck: down one, right one.
                Spring( self.pucks[o_index], self.pucks[o_index+(grid_y_n-1)], spring_length_m, spring_strength_Npm2, 
                        color=THECOLORS["lightblue"], c_damp=spring_damping)
                # Connect to a nearby puck: up one, right one.
                Spring( self.pucks[o_index-1], self.pucks[o_index+(grid_y_n)], spring_length_m, spring_strength_Npm2, 
                        color=THECOLORS["lightblue"], c_damp=spring_damping)

        # Throw the jello. Use a random speed.
        if type(speed) is tuple:
            speed_mps = random.uniform(speed[0], speed[1])
        else:
            speed_mps = speed

        # Use the angle of the grid to determine the direction.
        velocity_2d_mps = pos_x_delta_2d_m.set_magnitude( speed_mps)
        if velocity_2d_mps.length_squared() > 0.1:
            print("Throwing the jello against the wall.")

        for puck in self.pucks:
            puck.vel_2d_mps = velocity_2d_mps

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

    def update_PuckSpeedAndPosition(self, puck, dt_s):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/dt_s)
        
        # Acceleration from Newton's law.
        acc_2d_mps2 = puck_forces_2d_N / puck.mass_kg
        
        # Limit the absolute value of the acceleration components.
        limit_mps2 = 1000.0  # m/s^2
        acc_2d_mps2 = Vec2D(min(max(acc_2d_mps2.x, -limit_mps2), limit_mps2),
                            min(max(acc_2d_mps2.y, -limit_mps2), limit_mps2))
        
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
        self.tangled = False

        for i, puck in enumerate(self.pucks):
            # Wall collisions
            if not self.inhibit_wall_collisions:
                if (((puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]) or ((puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"])):
                    
                    if self.correct_for_wall_penetration:
                        if (puck.pos_2d_m.y - puck.radius_m) < self.walls["B_m"]:
                            penetration_y_m = self.walls["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                            puck.pos_2d_m.y += 2 * penetration_y_m
                    
                        if (puck.pos_2d_m.y + puck.radius_m) > self.walls["T_m"]:
                            penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls["T_m"]
                            puck.pos_2d_m.y -= 2 * penetration_y_m
                    
                    puck.vel_2d_mps.y *= -1 * min(self.coef_rest, puck.coef_rest)
                
                if (((puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]) or ((puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"])):
                    
                    if self.correct_for_wall_penetration:
                        if (puck.pos_2d_m.x - puck.radius_m) < self.walls["L_m"]:
                            penetration_x_m = self.walls["L_m"] - (puck.pos_2d_m.x - puck.radius_m)
                            puck.pos_2d_m.x += 2 * penetration_x_m
                    
                        if (puck.pos_2d_m.x + puck.radius_m) > self.walls["R_m"]:
                            penetration_x_m = (puck.pos_2d_m.x + puck.radius_m) - self.walls["R_m"]
                            puck.pos_2d_m.x -= 2 * penetration_x_m
                            
                    #print("CR x wall, puck:", self.coef_rest, puck.coef_rest)                    
                    puck.vel_2d_mps.x *= -1 * min(self.coef_rest, puck.coef_rest)
                
            # Collisions with other pucks. 
            for otherpuck in self.pucks[i+1:]:
                # Check if the two puck circles are overlapping.
                
                # Parallel to the normal
                puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                # Parallel to the tangent
                tangent_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)
                
                # distance between the two puck centers, squared
                p_to_p_m2 = puck_to_puck_2d_m.length_squared()
                
                # sum of the radii of the two pucks, squared
                r_plus_r_m2 = (puck.radius_m + otherpuck.radius_m)**2
                
                if (p_to_p_m2 < (1.1 * r_plus_r_m2)):
                    self.tangled = True
                
                # Keep this check fast by avoiding square roots.
                if (p_to_p_m2 < r_plus_r_m2):
                    self.collision_count += 1
                    
                    # If it's a bullet coming from another client, add to the
                    # hit count for non-bullet client.
                    if (otherpuck.client_name != None):
                        if (puck.client_name != otherpuck.client_name): 
                            if (otherpuck.bullet and (not puck.bullet)):
                                if puck.gun and puck.gun.shield:
                                    puck.gun.shield_hit_count += 1
                                    puck.gun.shield_hit = True
                                    puck.gun.shield_hit_duration_s = 0.0
                                else:
                                    puck.bullet_hit_count += 1
                                    puck.hit = True
                                    puck.hitflash_duration_timer_s = 0.0
                    
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
                        
                        # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restitution).
                        # of 1 here to better avoid stickiness.
                        CR_puck = 1
                        puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                                                       
                        # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
                        # This will put the pucks where they should have been at the time of collision detection.
                        puck.pos_2d_m = puck.pos_2d_m + (puck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))
                        otherpuck.pos_2d_m = otherpuck.pos_2d_m + (otherpuck_normal_AFTER_mps * (penetration_time_scaler * penetration_time_s))
                           
                    # Assign the AFTER velocities (using the actual CR here) to the puck for use in the next frame calculation.
                    CR_puck = min(puck.coef_rest, otherpuck.coef_rest)
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
    # Note: still floating values here)
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
                    print("all puck speeds set to zero")
                
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
        # Yes, that's right y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld(Vec2D(self.width_px, 0))
        
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
        
def make_some_pucks(demo):
    game_window.update_caption("Air Table: Demo #" + str(demo))
    env.fr_avg.reset()
    air_table.coef_rest = 1.00
    env.tickCount = 0
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
                if ((j,k) == (1,1)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3, color=puck_color_value)
    
    elif demo == 3:
        spacing_factor = 1.5
        grid_size = 5,3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
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

    window_dimensions_px = (800, 700)   #window_width_px, window_height_px

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = AirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})

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

    server = GameServer(host='0.0.0.0', port=5000, 
                        update_function=custom_update, clientStates=env.clients, 
                        signInOut_function=signInOut_function)
    
    # Limit the framerate, but let it float below this limit.
    framerate_limit = 480

    while True:
        env.tickCount += 1    
        dt_physics_s = float(myclock.tick( framerate_limit) * 1e-3)
        
        # Get input from local user.
        resetmode = env.get_local_user_input()
        
        # Get input from network clients.
        
        # This dt check avoids problem when dragging the game window.
        if ( (dt_physics_s < 0.10) and (not air_table.stop_physics) ):
            
            # Reset the game based on local user control.
            if resetmode in [0,1,2,3,4,5,6,7,8,9]:
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
                air_table.update_PuckSpeedAndPosition( eachpuck, dt_physics_s)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions()
            
            if env.tickCount > 10:
                env.fr_avg.update( myclock.get_fps())
            
            if (env.render_timer_s > env.dt_render_limit_s):
                
                # Erase the blackboard.
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
                
                # Display game timer text.
                if (demo_index == 8):
                    display_number(air_table.game_time_s, fnt_gameTimer, mode='gameTimer')
                
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
                    if ((client_name != 'local') and client.active):
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