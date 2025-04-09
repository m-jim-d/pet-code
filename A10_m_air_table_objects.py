#!/usr/bin/env python3

# Filename: A10_m_air_table_objects.py

"""
Core objects for the air table physics simulation.

This module defines the physical objects that can exist in the simulation:

Classes:
    Puck: Dynamic objects with physics properties (mass, velocity, etc.)  
    Spring: Elastic connections between pucks with customizable properties  
"""

import math
from typing import Optional

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A10_m_globals as g


class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, vel_2d_mps=Vec2D(0.0,0.0), 
                       c_drag=0.0, coef_rest=0.85, CR_fixed=False,
                       hit_limit=50.0, show_health=False, age_limit_s=3.0,
                       color=THECOLORS["gray"], client_name=None, bullet=False, pin=False, border_px=3,
                       groupIndex=0):
        
        self.radius_m = radius_m
        self.diameter_m = 2 * radius_m
        self.radius_px = round(g.env.px_from_m(self.radius_m))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.c_drag = c_drag
        
        self.coef_rest = coef_rest
        self.coef_rest_atBirth = coef_rest
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
        self.border_thickness_px = border_px
        
        self.client_name = client_name
        self.tube: Optional[Tube] = None
        self.jet: Optional[Jet] = None
        self.gun: Optional[Gun] = None
        
        self.hit = False
        self.hitflash_duration_timer_s = 0.0
        # Make the hit flash persist for this number of seconds:
        self.hitflash_duration_timer_limit_s = 0.05
        self.show_health = show_health
        
        # bullet nature
        self.bullet = bullet
        self.birth_time_s = g.air_table.time_s
        self.age_limit_s = age_limit_s
        
        # Keep track of health.
        self.bullet_hit_count = 0
        self.bullet_hit_limit = hit_limit

        self.groupIndex = groupIndex

        self.pin = pin
        # Add puck to the lists of pucks, controlled pucks, and target pucks.
        if not pin:
            g.air_table.pucks.append(self)
            
            if not self.bullet:
                if self.client_name:
                    g.air_table.controlled_pucks.append(self)
                
    # If you print an object instance...
    def __str__(self):
        return f"puck: x is {self.pos_2d_m.x}, y is {self.pos_2d_m.y}"
        
    def set_pos_and_vel(self, pos_2d_m, vel_2d_m=Vec2D(0,0)):
        # Update our vectors
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_m

    def delete(self):
        if (not self.bullet):
            # Delete any springs that connect this puck to other pucks.
            for spring in g.air_table.springs[:]:
                if (spring.p1 == self) or (spring.p2 == self):
                    g.air_table.springs.remove( spring)
            
            # If a client has selected this puck (a cursor string connected),
            # unselect it so the cursor string won't continue to be drawn. 
            for client_name in g.env.clients:
                client = g.env.clients[client_name]
                if client.selected_puck == self:
                    client.selected_puck = None

            # Remove the puck from special lists.
            if self in g.air_table.controlled_pucks: 
                g.air_table.controlled_pucks.remove(self)
        
        g.air_table.pucks.remove(self)
    
    def calc_regularDragForce(self):  
        self.puckDrag_force_2d_N = self.vel_2d_mps * -1 * self.c_drag
    
    def draw(self, tempColor=None):
        # Convert x,y to pixel screen location and then draw.
        self.pos_2d_px = g.env.ConvertWorldToScreen( self.pos_2d_m)
        
        # Update based on zoom factor in px_from_m.
        self.radius_px = round(g.env.px_from_m( self.radius_m))
        if (self.radius_px < 2):
            self.radius_px = 2
                    
        # Draw main puck body.
        pygame.draw.circle( g.game_window.surface, self.color, self.pos_2d_px, self.radius_px, g.env.zoomLineThickness(self.border_thickness_px))
                                           
                                   
class Spring:
    def __init__(self, p1, p2, length_m=3.0, strength_Npm=0.5, pin_radius_m=0.05,
        color=THECOLORS["dodgerblue"], width_m=0.025, c_damp=0.5, c_drag=0.0):
        
        # Optionally this spring can have one end pinned to a vector point. Do this by
        # passing in p2 as a vector.
        if (p2.__class__.__name__ == 'Vec2D'):
            # Create a point puck at the pinning location. The location of this point puck
            # will never change because it is not in the pucks list that is processed by
            # the physics engine.
            p2 = Puck( p2, pin_radius_m, 1.0, pin=True, border_px=0, color=THECOLORS['white'])
            length_m = 0.0
        
        self.p1 = p1
        self.p2 = p2
        self.p1p2_separation_2d_m = Vec2D(0,0)
        self.p1p2_separation_m = 0
        self.p1p2_normalized_2d = Vec2D(0,0)
        
        self.length_m = length_m
        self.strength_Npm = strength_Npm
        self.damper_Ns2pm2 = c_damp
        self.unstretched_width_m = width_m # 0.05
        
        self.c_drag = c_drag
        
        self.spring_vertices_2d_m = []
        self.spring_vertices_2d_px = []
        
        self.color = color
        self.draw_as_line = False
        
        # Automatically add this spring to the air_table springs list
        g.air_table.springs.append(self)
    
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
        
        # This force acts in opposite directions for each of the two pucks. Notice the
        # "+=" here, this is an aggregate across all the springs. This aggregate MUST be
        # reset (zeroed) after the movements are calculated. So by the time you've looped
        # through all the springs, you get the NET force, on each puck, applied by all the
        # individual springs.
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
        # Change the width to indicate the stretch or compression in the spring. Note,
        # it's good to do this outside of the main calc loop (using the rendering timer).
        # No need to do all this each time step.
        
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
            self.spring_vertices_2d_px.append( g.env.ConvertWorldToScreen( vertice_2d_m))
        
        # Draw the spring
        if self.draw_as_line == True:
            pygame.draw.aaline(g.game_window.surface, self.color, g.env.ConvertWorldToScreen(self.p1.pos_2d_m),
                                                                       g.env.ConvertWorldToScreen(self.p2.pos_2d_m))
        else:
            pygame.draw.polygon(g.game_window.surface, self.color, self.spring_vertices_2d_px)

        if self.p2.pin: self.p2.draw()
