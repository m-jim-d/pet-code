#!/usr/bin/env python3

# Filename: A14_m_air_table_objects.py

import math
from typing import Optional

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A10_m_globals as g
from A10_m_air_table_objects import Puck, Spring
from A13_m_air_table_objects import Tube, Jet


class Gun(Tube):
    def __init__(self, puck):
        # Associate the gun with the puck (referenced in the Tube class).
        super().__init__(puck)
        
        # Degrees of rotation per rendering cycle.
        self.rotation_deg = 2.0
        
        self.color = self.client.cursor_color
        
        self.rotate_everything( 45)
        
        self.bullet_speed_mps = 5.0
        self.fire_time_s = g.air_table.time_s
        self.firing_delay_s = 0.1
        self.testing_gun = False

        # Set a negative group index for bullet stream (inhibit collisions with itself)
        if self.puck.client_name == "local":
            self.groupIndex = -100
        else:
            self.groupIndex = -int(self.puck.client_name[1:])        
        self.shield = None
    
    def control_firing(self):
        if ((self.client.key_i == "D") or self.testing_gun):
            if ((g.air_table.time_s - self.fire_time_s) > self.firing_delay_s):
                self.fire_gun()
                # Timestamp the firing event.
                self.fire_time_s = g.air_table.time_s

    def fire_gun(self):
        bullet_radius_m = 0.05
        # Set the initial position of the bullet so that it clears (doesn't collide with) the host puck.
        initial_position_2d_m = (self.puck.pos_2d_m +
                                (self.direction_2d_m * (1.1 * self.puck.radius_m + 1.1 * bullet_radius_m)) )
        temp_bullet = Puck(initial_position_2d_m,  bullet_radius_m, 0.3, groupIndex=self.groupIndex)
        
        # Relative velocity of the bullet: the bullet velocity as seen from the host puck. This is the
        # speed of the bullet relative to the motion of the host puck (host velocity BEFORE the firing of 
        # the bullet).
        bullet_relative_vel_2d_mps = self.direction_2d_m * self.bullet_speed_mps
        
        # Absolute velocity of the bullet.
        temp_bullet.vel_2d_mps = self.puck.vel_2d_mps + bullet_relative_vel_2d_mps
        
        temp_bullet.bullet = True
        temp_bullet.color = g.env.clients[self.puck.client_name].cursor_color
        temp_bullet.client_name = self.puck.client_name
        
        # Calculate the recoil impulse from firing the gun (opposite the direction of the bullet).
        self.puck.impulse_2d_Ns = bullet_relative_vel_2d_mps * temp_bullet.mass_kg * (-1)
    
    def draw(self):
        # Draw the gun tube.
        line_thickness = 3
        pygame.draw.polygon(g.game_window.surface, self.color, 
                 self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.puck.pos_2d_m), line_thickness)
                
    def control_shield(self):
        pass
    def draw_shield(self):
        pass
