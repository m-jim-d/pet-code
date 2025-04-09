#!/usr/bin/env python3

# Filename: A11_m_air_table_objects.py

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
    def __init__(self, tube_base_2d_m, client_name):
        self.client = g.env.clients[client_name]
        self.color = self.client.cursor_color
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 360.0
        
        # Scaling factors to manage the aspect ratio of the tube.
        self.sf_x = 0.15
        self.sf_y = 0.50

        # The point about which the tube rotates.
        self.tube_base_2d_m = tube_base_2d_m
        
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
            vertices_2d_px.append( g.env.ConvertWorldToScreen(vertex_2d_m + base_point_2d_m))
        return vertices_2d_px
        
    def client_rotation_control(self):
        if (self.client.key_a == "D"):
            self.rotate_everything( +1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_d == "D"):
            self.rotate_everything( -1 * self.rotation_rate_dps * g.env.dt_render_limit_s)
        
    def draw_tube(self, line_thickness=3):
        # Draw the tube on the game-window surface.
        pygame.draw.polygon(g.game_window.surface, self.color, 
                            self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.tube_base_2d_m), g.env.zoomLineThickness(line_thickness))

    def delete(self):
        g.air_table.raw_tubes.remove(self)
