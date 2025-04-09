#!/usr/bin/env python3

# Filename: A12_m_air_table_objects.py

import math
from typing import Optional

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A10_m_globals as g
from A10_m_air_table_objects import Puck, Spring

class Tube:
    def __init__(self, puck, sf_abs=False):
        # Associate the tube with the puck.
        self.puck = puck
        self.client = g.env.clients[self.puck.client_name]
        self.color = self.client.cursor_color
        
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
                    
    def client_rotation_control(self):
        if (self.client.key_j == "D"):
            self.rotate_everything( +1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_l == "D"):
            self.rotate_everything( -1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
                    
    def convert_from_world_to_screen(self, vertices_2d_m, base_point_2d_m):
        vertices_2d_px = []
        for vertex_2d_m in vertices_2d_m:
            # Calculate absolute position of this vertex.
            vertices_2d_px.append( g.env.ConvertWorldToScreen(vertex_2d_m + base_point_2d_m))
        return vertices_2d_px
        
    def draw_tube(self, line_thickness=3):
        # Draw the tube on the game-window surface. Establish the base_point as the center
        # of the puck.
        pygame.draw.polygon(g.game_window.surface, self.color, 
                            self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.puck.pos_2d_m), g.env.zoomLineThickness(line_thickness))

    def delete(self):
        g.air_table.raw_tubes.remove(self)


class Jet(Tube):
    def __init__(self, puck, sf_abs=True):
        # Associate the jet with the puck (referenced in the Tube class).
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
        
        # Point everything down for starters.
        self.rotate_everything( 180)
        
    def turn_jet_forces_onoff(self):
        pass
            
    def client_rotation_control(self):
        if (self.client.key_a == "D"):
            self.rotate_everything( +1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_d == "D"):
            self.rotate_everything( -1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_s == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_jet_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_jet_angle)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the direction
            # once but not keep flipping. This first line is enough to keep the local
            # client from flipping again because the local keyboard doesn't keep sending
            # the "D" event if the key is held down.
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
        
        # Draw a little nose cone on the other side of the puck from the jet. This is a
        # visual aid to help the player see the direction the puck will go when the jet is
        # on.
        pygame.draw.polygon(g.game_window.surface, THECOLORS["yellow1"], 
                            self.convert_from_world_to_screen(self.nose_vertices_2d_m, self.puck.pos_2d_m), 0)
        
        # Draw the red flame.
        if (self.client.key_w == "D"):
            pygame.draw.polygon(g.game_window.surface, THECOLORS["red"], 
                                self.convert_from_world_to_screen(self.flame_vertices_2d_m, self.puck.pos_2d_m), 0)
