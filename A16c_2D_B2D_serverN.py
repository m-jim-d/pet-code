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

# Import the vector class from a local module (in this same directory)
from A09_vec2d import Vec2D

from A08_network import GameServer, RunningAvg, setClientColors

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
                #self.selected_puck.selected = False
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

      
class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, vel_2d_mps=Vec2D(0.0,0.0),
                       c_drag=0.0, c_angularDrag=0.0, coef_rest=0.85, CR_fixed=False,
                       hit_limit=50.0, show_health=False,
                       color=THECOLORS["gray"], client_name=None, bullet=False, pin=False,
                       rect_fixture=False, aspect_ratio=1.0, border_px=3):
        
        self.radius_m = radius_m
        self.radius_px = round(env.px_from_m(self.radius_m * env.viewZoom))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.c_drag = c_drag
        self.c_angularDrag = c_angularDrag
        self.coef_rest = coef_rest
        self.CR_fixed = CR_fixed
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_mps
        self.rotation_speed = 0.0
        
        self.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        self.jet_force_2d_N = Vec2D(0.0,0.0)
        self.puckDrag_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_torque_force_Nm = 0

        # Non-center of mass (COM).  #b2d
        # This is a list of dictionaries: each dictionary contains a force and a body location
        self.nonCOM_N = []
        
        self.impulse_2d_Ns = Vec2D(0.0,0.0)
        
        self.color = color
        self.border_thickness_px = border_px
        
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
        
        # Create a Box2d puck.
        self.aspect_ratio = aspect_ratio
        self.rect_fixture = rect_fixture
        if (not pin):
            self.b2d_body = self.create_Box2d_Puck()
            air_table.puck_dictionary[self.b2d_body] = self

            air_table.pucks.append(self)

            if not self.bullet:
                air_table.target_pucks.append(self)
                if self.client_name:
                    air_table.controlled_pucks.append(self)
                
    # If you print an object instance...
    def __str__(self):
        return f"puck: x is {self.pos_2d_m.x}, y is {self.pos_2d_m.y}"
    
    # Box2d
    def create_Box2d_Puck(self):
        # Create a dynamic body
        dynamic_body = b2_world.CreateDynamicBody(position=b2Vec2(self.pos_2d_m.tuple()), angle=0, 
                                                  linearVelocity=b2Vec2(self.vel_2d_mps.tuple()))
        
        # Surface friction
        coef_friction = air_table.coef_friction_puck
        
        if self.rect_fixture:
            # And add a box fixture onto it.
            dynamic_body.CreatePolygonFixture(box=(self.radius_m, self.radius_m * self.aspect_ratio), density=self.density_kgpm2, 
                                              friction=coef_friction, restitution=self.coef_rest)
                                              
            # Set the mass attribute based on what box2d calculates.
            self.mass_kg = dynamic_body.mass
            
        else:
            # And add a circle fixture onto it.
            dynamic_body.CreateCircleFixture(radius=self.radius_m , density=self.density_kgpm2, 
                                             friction=coef_friction, restitution=self.coef_rest)
        
        # fluid drag inside Box2D
        # Note that linear damping is accounted for external to box2d using the c_drag attribute.
        dynamic_body.linearDamping = 0.0 # This must stay 0.0 to avoid double-counting the damping.
        dynamic_body.angularDamping = self.c_angularDrag
        
        return dynamic_body
    
    # Box2d
    def get_Box2d_XandV(self):
        # Position
        box2d_pos_2d_m = self.b2d_body.GetWorldPoint(b2Vec2(0,0))
        self.pos_2d_m = Vec2D( box2d_pos_2d_m.x, box2d_pos_2d_m.y)
        
        # Velocity
        box2d_vel_2d_m = self.b2d_body.linearVelocity
        self.vel_2d_mps = Vec2D( box2d_vel_2d_m.x, box2d_vel_2d_m.y)
        
        # Rotational speed.
        self.rotation_speed = self.b2d_body.angularVelocity
    
    def delete(self):
        # Remove the puck from the dictionary.
        del air_table.puck_dictionary[self.b2d_body]
        # Remove the puck from the world in box2d.
        b2_world.DestroyBody(self.b2d_body)

        if (not self.bullet):
            # Delete any springs that connect this puck to other pucks.
            for spring in air_table.springs[:]:
                if (spring.p1 == self) or (spring.p2 == self):
                    air_table.springs.remove( spring)
            
            # Remove the puck from special lists.
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
            puck_border_thickness = self.border_thickness_px
            puck_color = self.color
        
        if self.rect_fixture:
            # Box2d
            fixture_shape = self.b2d_body.fixtures[0].shape
            vertices_screen_2d_px = []
            for vertex_object_2d_m in fixture_shape.vertices:
                vertex_world_2d_m = self.b2d_body.transform * vertex_object_2d_m  # Overload operation
                vertex_screen_2d_px = env.ConvertWorldToScreen( Vec2D(vertex_world_2d_m.x, vertex_world_2d_m.y)) # This returns a tuple
                vertices_screen_2d_px.append( vertex_screen_2d_px) # Append to the list.
            pygame.draw.polygon(game_window.surface, puck_color, vertices_screen_2d_px, env.zoomLineThickness(puck_border_thickness))
            
        else:
            # Draw main puck body.
            pygame.draw.circle( game_window.surface, puck_color, self.pos_2d_px, self.radius_px, env.zoomLineThickness(puck_border_thickness))
            
            # If it's not a bullet and not a rectangle, draw a spoke to indicate rotational orientation.
            if ((self.bullet == False) and (self.rect_fixture==False)):
                # Shorten the spoke by a fraction of the thickness so that its end (and the blocky rendering) is hidden in the border.
                reduction_m = env.px_to_m * self.border_thickness_px * 0.50
                point_on_radius_b2d_m = self.b2d_body.GetWorldPoint( b2Vec2(0.0, self.radius_m - reduction_m))
                point_on_radius_2d_m = Vec2D( point_on_radius_b2d_m.x, point_on_radius_b2d_m.y)
                point_on_radius_2d_px = env.ConvertWorldToScreen( point_on_radius_2d_m)
                
                point_at_center_b2d_m = self.b2d_body.GetWorldPoint( b2Vec2(0.0, 0.0))
                point_at_center_2d_m = Vec2D( point_at_center_b2d_m.x, point_at_center_b2d_m.y)
                point_at_center_2d_px = env.ConvertWorldToScreen( point_at_center_2d_m)

                pygame.draw.line(game_window.surface, puck_color, point_on_radius_2d_px, point_at_center_2d_px, env.zoomLineThickness(puck_border_thickness))
                # Round the end of the spoke that is at the center of the puck.
                #pygame.draw.circle( game_window.surface, puck_color, self.pos_2d_px, 0.7 *env.zoomLineThickness(puck_border_thickness), 0)
        
        # Draw life (poor health) indicator circle.
        if (not self.bullet and self.show_health):
            spent_fraction = float(self.bullet_hit_count) / float(self.bullet_hit_limit)
            
            if self.rect_fixture:
                life_radius_px = spent_fraction * self.radius_px * self.aspect_ratio
            else:
                life_radius_px = spent_fraction * self.radius_px
            
            if (life_radius_px < 2.0):
                life_radius_px = 2.0
            
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
        
        # Also set the velocity of the Box2d puck.
        temp_bullet.b2d_body.linearVelocity = b2Vec2( temp_bullet.vel_2d_mps.tuple())
        
        temp_bullet.bullet = True
        temp_bullet.b2d_body.bullet = True
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


class fwQueryCallback( b2QueryCallback):
    # Box2D checks for objects at particular location (p), e.g. under the cursor.
    def __init__(self, p): 
        super().__init__()
        self.point = p
        self.fixture = None

    def ReportFixture(self, fixture):
        body = fixture.body
        if body.type == b2_dynamicBody:
            inside=fixture.TestPoint(self.point)
            if inside:
                self.fixture=fixture
                # We found the object, so stop the query
                return False
        # Continue the query
        return True
            

class AirTable:
    def __init__(self, walls_dic):
        self.gON_2d_mps2 = Vec2D(-0.0, -9.8)
        self.gOFF_2d_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_2d_mps2
        self.g_ON = False
        
        self.b2_walls = []
        
        self.pucks = []
        self.puck_dictionary = {}
        self.controlled_pucks = []
        self.target_pucks = []
        self.springs = []
        self.walls = walls_dic
        self.collision_count = 0
        self.coef_friction_puck = 0.2 # all pucks
        
        self.color_transfer = False
        
        self.stop_physics = False
        self.tangled = False

        self.jello_tangle_checking_enabled = False
        
        self.FPS_display = True

        # General clock time for determining bullet age.
        self.time_s = 0.0
        # Timer for the Jello Madness game.
        self.game_time_s = 0.0
        self.tangle_checker_time_s = 0.0

    def buildControlledPuck(self, x_m=1.0, y_m=1.0, r_m=0.45, density=0.7, c_drag=0.7, client_name=None, sf_abs=True):
        tempPuck = Puck( Vec2D( x_m, y_m), r_m, density, c_drag=c_drag, c_angularDrag=0.5,
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
                      c_drag=puck_drag, c_angularDrag=0.3,
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
            puck.b2d_body.linearVelocity = velocity_2d_mps.tuple()
                             
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
    
    def checkForPuckAtThisPosition_b2d(self, x_px_or_tuple, y_px = None):
        # This is used for cursor selection at a particular point on the puck.  #b2d
        # Return the selected puck and also the local point on the puck.
        
        selected_puck = None
        
        if y_px == None:
            self.x_px = x_px_or_tuple[0]
            self.y_px = x_px_or_tuple[1]
        else:
            self.x_px = x_px_or_tuple
            self.y_px = y_px
        
        # Convert to a world point.
        test_position_2d_m = env.ConvertScreenToWorld(Vec2D(self.x_px, self.y_px))
        
        # Convert this to a box2d vector.
        p = b2Vec2( test_position_2d_m.tuple())
        
        # Make a small box.
        aabb = b2AABB( lowerBound=p-(0.001, 0.001), upperBound=p+(0.001, 0.001))

        # Query the world for overlapping shapes.
        query = fwQueryCallback( p)
        b2_world.QueryAABB( query, aabb)
        
        # If the query was successful and found a body at the cursor point.
        if query.fixture:
            selected_b2d_body = query.fixture.body
            selected_b2d_body.awake = True
        
            # Find the local point in the body's coordinate system.
            local_b2d_m = selected_b2d_body.GetLocalPoint( p)
        
            # Use a dictionary to identify the puck based on the b2d body.
            # Bullets have not been added to the dictionary.
            if not selected_b2d_body.bullet:
                selected_puck = air_table.puck_dictionary[ selected_b2d_body]
        
            # Return a dictionary with the puck and local selection point on it.
            return {'puck': selected_puck, 'b2d_xy_m': local_b2d_m}
        
        else:
            return {'puck': None, 'b2d_xy_m': b2Vec2(0,0)}
    
    def update_TotalForceVectorOnPuck(self, puck, dt_s):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.puckDrag_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/dt_s)
        
        # Apply this force to the puck's center of mass (COM) in the Box2d world
        force_point_b2d_m = puck.b2d_body.GetWorldPoint( b2Vec2(0,0))
        force_vector_b2d_N = b2Vec2( puck_forces_2d_N.tuple())
        puck.b2d_body.ApplyForce( force=force_vector_b2d_N, point=force_point_b2d_m, wake=True)
        
        # Apply any non-COM forces.   #b2d
        for force_dict in puck.nonCOM_N:
            force_point_b2d_m = puck.b2d_body.GetWorldPoint( force_dict['local_b2d_m'])
            force_vector_b2d_N = b2Vec2( force_dict['force_2d_N'].tuple())
            puck.b2d_body.ApplyForce( force=force_vector_b2d_N, point=force_point_b2d_m, wake=True)
        
        # Apply torques.   #b2d
        puck.b2d_body.ApplyTorque( puck.cursorString_torque_force_Nm, wake=True)
        
        # Now reset the aggregate forces.
        puck.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        puck.nonCOM_N = []
        puck.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_torque_force_Nm = 0.0
        
        puck.impulse_2d_Ns = Vec2D(0.0,0.0)
    
    def check_for_jello_tangle(self):
        if air_table.tangle_checker_time_s > 0.1:
            air_table.tangle_checker_time_s = 0.0
            
            self.tangled = False
            for i, puck in enumerate(self.pucks):
                # Contacts with other pucks. 
                for otherpuck in self.pucks[i+1:]:
                    # Check if the two puck circles are overlapping.
                    # parallel to the normal
                    puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                    
                    # Keep the following checks fast by avoiding square roots.
                    # separation between the pucks, squared (not a vector)
                    p_to_p_m2 = puck_to_puck_2d_m.length_squared()
                    
                    # sum of the radii of the two pucks, squared
                    r_plus_r_m2 = (puck.radius_m + otherpuck.radius_m)**2
                    
                    # A check for the Jello-madness game. If it's tangled, balls
                    # will be close and this will be set to True.
                    if (p_to_p_m2 < 1.1 * r_plus_r_m2):
                        self.tangled = True
                

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
            
    def adjust_restitution_for_gravity(self):
        if air_table.g_ON:
            air_table.g_2d_mps2 = air_table.gON_2d_mps2
            # Box2d...
            for eachpuck in air_table.pucks:
                eachpuck.b2d_body.fixtures[0].restitution = eachpuck.coef_rest
                eachpuck.b2d_body.fixtures[0].friction = air_table.coef_friction_puck
        else:
            air_table.g_2d_mps2 = air_table.gOFF_2d_mps2
            # Box2d...
            for eachpuck in air_table.pucks:
                if not eachpuck.CR_fixed:
                    eachpuck.b2d_body.fixtures[0].restitution = 1.0
                    # Apply this also to the puck friction. There is no corresponding "fixed" setting for friction.
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
                    
                # Control physics for Jello Madness
                elif ((event.key==K_p) and not self.shift_key_down()):
                    air_table.stop_physics = not air_table.stop_physics
                    if (not air_table.stop_physics):
                        air_table.game_time_s = 0
                        print("game loop is active again")
                    else:
                        print("game loop is paused")
                
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
        # Yes, that's right y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld( Vec2D( self.width_px, 0))
        
        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode( screen_tuple_px)

        self.update_caption( title)
        
        self.surface.fill( THECOLORS["black"])
        pygame.display.update()
        
    def update_caption(self, title):
        pygame.display.set_caption( title)
        self.caption = title
    
    def update(self):
        pygame.display.update()
        
    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill( THECOLORS["black"])
        pygame.display.update()


class myContactListener(b2ContactListener):
    def __init__(self):
        super().__init__()

    def BeginContact(self, contact):
        # Check if both bodies are in the puck dictionary
        bodyA = contact.fixtureA.body
        bodyB = contact.fixtureB.body

        if (bodyA in air_table.puck_dictionary) and (bodyB in air_table.puck_dictionary):
            puckA = air_table.puck_dictionary[bodyA]
            puckB = air_table.puck_dictionary[bodyB]

            # Handle bullet collisions from either puck
            # Exclude the case where it's your own bullet hitting you.
            if puckA.client_name != puckB.client_name:
                # Case 1: puckB is bullet, puckA is target
                if (puckB.client_name != None) and (puckB.bullet and (not puckA.bullet)):
                    if puckA.gun and puckA.gun.shield:
                        puckA.gun.shield_hit_count += 1
                        puckA.gun.shield_hit = True
                        puckA.gun.shield_hit_duration_s = 0.0
                    else:
                        puckA.bullet_hit_count += 1
                        puckA.hit = True
                        puckA.hitflash_duration_timer_s = 0.0
                # Case 2: puckA is bullet, puckB is target
                elif (puckA.client_name != None) and (puckA.bullet and (not puckB.bullet)):
                    if puckB.gun and puckB.gun.shield:
                        puckB.gun.shield_hit_count += 1
                        puckB.gun.shield_hit = True
                        puckB.gun.shield_hit_duration_s = 0.0
                    else:
                        puckB.bullet_hit_count += 1
                        puckB.hit = True
                        puckB.hitflash_duration_timer_s = 0.0

#===========================================================
# Functions
#===========================================================
        
def make_some_pucks(demo):
    game_window.update_caption("PyBox2D Air-Table Server A16c     Demo #" + str(demo))
    env.constant_dt_s = None

    env.fr_avg.reset()
    env.tickCount = 0
    
    # These two Puck-Popper demos should NOT have gravity unless turned on during the game.
    if demo in [7,9]:
        air_table.g_ON = False

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
            {"p1": {"rps": 4.0,  "color": THECOLORS["white"]},
             "p2": {"rps": 30.0, "color": THECOLORS["darkred"]},
             "p3": {"rps": -34.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps": 2.0,  "color": THECOLORS["white"]},
             "p2": {"rps": 4.0,  "color": THECOLORS["darkred"]},
             "p3": {"rps": -6.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps": 11.0,  "color": THECOLORS["white"]},
             "p2": {"rps": 0.0,  "color": THECOLORS["blue"]},
             "p3": {"rps": 0.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps": 2.0,  "color": THECOLORS["darkred"]},
             "p2": {"rps": 2.0,  "color": THECOLORS["darkred"]},
             "p3": {"rps": 2.0,  "color": THECOLORS["darkred"]}}
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
        
        p2 = Puck(Vec2D(8.0, 2.5), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]
        p2.b2d_body.fixtures[0].friction = 2.0

        p3 = Puck(Vec2D(5.0, 7.5), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p3"]["color"])
        p3.b2d_body.angularVelocity = state["p3"]["rps"]
        p3.b2d_body.fixtures[0].friction = 2.0

        spring_strength_Npm2 = 15.0
        spring_length_m = 1.0
        spring_width_m = 0.10
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p1, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
    
    elif demo == 3:
        onePi = round( 1.0 * math.pi, 2)
        initial_states = [
            {"p1": {"rps": 4.0,    "color": THECOLORS["brown"]},
             "p2": {"rps": 2.0,    "color": THECOLORS["tan"]}},

            {"p1": {"rps": 2.0,    "color": THECOLORS["tan"]},
             "p2": {"rps": 4.0,    "color": THECOLORS["brown"]}},

            {"p1": {"rps": onePi,  "color": THECOLORS["tan"]},
             "p2": {"rps": onePi,  "color": THECOLORS["tan"]}},

            {"p1": {"rps": 0.0,    "color": THECOLORS["white"]},
             "p2": {"rps": 2.0,    "color": THECOLORS["tan"]}},

            {"p1": {"rps": -onePi, "color": THECOLORS["tan"]},
             "p2": {"rps": -onePi, "color": THECOLORS["tan"]}}
        ]
        env.d3_state_cnt = len(initial_states)

        state = initial_states[env.demo3_variation_index]
        print("Variation", env.demo3_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"])

        p1 = Puck(Vec2D(2.0, 2.0), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        p1.b2d_body.fixtures[0].friction = 2.0
        
        p2 = Puck(Vec2D(8.0, 6.75), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]
        p2.b2d_body.fixtures[0].friction = 2.0

        spring_strength_Npm2 = 15.0
        spring_length_m = 1.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.15, c_damp=50.0, color=THECOLORS["yellow"])
    
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

        tempPuck = Puck(Vec2D(8.2, 4.0), 1.5, density, rect_fixture=True, aspect_ratio=0.3, show_health=True)
        tempPuck.b2d_body.angularVelocity = 0.5
        Spring(tempPuck, Vec2D(8.2, 4.0), strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)
        
        tempPuck = Puck(Vec2D(3.0, 7.0), 1.4, density, rect_fixture=True, aspect_ratio=0.1, show_health=True)
        tempPuck.b2d_body.angularVelocity = -0.5
        Spring(tempPuck, Vec2D(3.0, 7.0), strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)

        # Make some pinned-spring pucks.
        for m in range(0, 6): 
            pinPoint_2d = Vec2D(2.0 + float(m) * 0.65, 4.0)
            tempPuck = Puck(pinPoint_2d, 0.25, density, color=THECOLORS["orange"], show_health=True, hit_limit=15)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # Make user/client controllable pucks
        # for all the clients.
        y_puck_position_m = 1.0
        for client_name in env.clients:
            client = env.clients[client_name]
            if client.active and not client.drone:
                air_table.buildControlledPuck( x_m=7.0, y_m=y_puck_position_m, r_m=0.45, client_name=client_name, sf_abs=False)
                y_puck_position_m += 1.2
                        
        # drone puck
        client_name = "C5"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=1.0, y_m=1.0, r_m=0.55, client_name=client_name, sf_abs=False)
        client_name = "C6"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=8.5, y_m=7.0, r_m=0.55, client_name=client_name, sf_abs=False)
            
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
    
    elif demo == 0:
        air_table.g_ON = True

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

    else:
        print("Nothing set up for this key.")

    # Now, after creating the pucks, set the restitution for gravity conditions.
    env.adjust_restitution_for_gravity()
    
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
    global env, game_window, air_table, b2_world
        
    pygame.init()

    myclock = pygame.time.Clock()

    window_dimensions_px = (800, 700)   #window_width_px, window_height_px   (800, 700)
    
    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = AirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})

    #=====================================================================
    # Box2d setup (start)
    #=====================================================================
    
    # Create the world
    b2_world = b2World(gravity=(-0.0, -0.0), doSleep=True, contactListener=myContactListener())

    # List of wall bodies.
    # Floor
    wall_body = b2_world.CreateStaticBody(position=(0.0, -1.0),
                   shapes=b2PolygonShape(box=(150, 1.0)) )
    air_table.b2_walls.append( wall_body)  
    
    # Ceiling
    wall_body = b2_world.CreateStaticBody(position=(0.0, game_window.UR_2d_m.y+1.0),
                   shapes=b2PolygonShape(box=(150, 1.0)) )
    air_table.b2_walls.append( wall_body)  
    
    # Left wall.
    wall_body = b2_world.CreateStaticBody(position=(-1.0, 0.0),
                   shapes=b2PolygonShape(box=(1.0, 150.0)) )
    air_table.b2_walls.append( wall_body)   
    
    # Right wall.
    wall_body = b2_world.CreateStaticBody(position=(game_window.UR_2d_m.x+1.0, 0.0),
                   shapes=b2PolygonShape(box=(1.0, 150.0)) )
    air_table.b2_walls.append( wall_body)   
    
    #=====================================================================
    # Box2d setup (end)
    #=====================================================================

    # Extend the clients dictionary to accommodate up to 10 network clients.
    for m in range(1,11):
        c_name = 'C' + str(m)
        env.clients[ c_name] = Client( env.client_colors[ c_name])

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
    
    # Font object for rendering text onto display surface.
    fnt_gameTimer = pygame.font.SysFont("Courier", 50)
        
    while True:
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
                
                # This should remove all references to the pucks and effectively delete them. 
                # First some Box2d clean-up.
                for eachpuck in air_table.pucks:
                    b2_world.DestroyBody(eachpuck.b2d_body)
                
                # Then all the lists.
                air_table.pucks = []
                air_table.puck_dictionary = {}
                air_table.controlled_pucks = []
                air_table.target_pucks = []
                air_table.springs = []

                # Most of the demos don't need the tangle checker.
                air_table.jello_tangle_checking_enabled = False
                
                # Now just black out the screen.
                game_window.clear()
                
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
            b2_world.Step( dt_physics_s, 10, 10)
            
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
