#!/usr/bin/env python3

# Filename: A15_air_table_objects.py

"""
Core objects for the air table physics simulation.

This module defines the physical objects that can exist in the simulation:

Classes:
    Wall: Static boundary objects with collision detection  
    Puck: Dynamic objects with physics properties (mass, velocity, etc.)  
    Spring: Elastic connections between pucks with customizable properties  
    RotatingTube: Base class for rotatable attachments (Jet/Gun)  
    Jet: Propulsion system that can be attached to pucks  
    Gun: Weapon system that can be mounted on pucks  

Walls and Puck supports Box2D integration for advanced physics simulation when enabled.
"""

import math
import random

from typing import Optional

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A15_globals as g

from Box2D import b2Vec2


class Wall:
    def __init__(self, pos_2d_m, half_width_m, half_height_m, angle_radians=0.0,
                       color=THECOLORS["gray"], border_px=3, fence=False):
        self.pos_2d_m = pos_2d_m
        self.half_width_m = half_width_m
        self.half_height_m = half_height_m
        self.angle_radians = angle_radians
        self.color = color
        self.border_px = border_px
        self.fence = fence

        self.b2d_body = self.create_Box2d_Wall()
        g.air_table.walls.append(self)

    def create_Box2d_Wall(self):
        # Create a static body
        static_body = g.air_table.b2d_world.CreateStaticBody(position=b2Vec2(self.pos_2d_m.tuple()), angle=self.angle_radians )
        
        # And add a box fixture onto it.
        static_body.CreatePolygonFixture(box=(self.half_width_m, self.half_height_m))
        return static_body

    def delete(self):
        # Remove the wall from the world in box2d.
        g.air_table.b2d_world.DestroyBody(self.b2d_body)        
        g.air_table.walls.remove( self)

    def draw(self):
        fixture_shape = self.b2d_body.fixtures[0].shape
        vertices_screen_2d_px = []
        for vertex_object_2d_m in fixture_shape.vertices:
            vertex_world_2d_m = self.b2d_body.transform * vertex_object_2d_m  # Overload operation
            vertex_screen_2d_px = g.env.ConvertWorldToScreen( Vec2D(vertex_world_2d_m.x, vertex_world_2d_m.y)) # This returns a tuple
            vertices_screen_2d_px.append( vertex_screen_2d_px) # Append to the list.
        pygame.draw.polygon(g.game_window.surface, self.color, vertices_screen_2d_px, g.env.zoomLineThickness(self.border_px))


class Puck:
    def __init__(self, pos_2d_m, radius_m, density_kgpm2, vel_2d_mps=Vec2D(0.0,0.0), 
                       angle_r=math.pi/2, angularVelocity_rps=0, showSpoke=True,
                       c_drag=0.0, coef_rest=0.85, CR_fixed=False,
                       hit_limit=50.0, show_health=False, age_limit_s=3.0,
                       color=THECOLORS["gray"], client_name=None, bullet=False, pin=False, border_px=3,
                       rect_fixture=False, hw_ratio=1.0, groupIndex=0, awake=True,
                       friction=0.2, friction_fixed=False, c_angularDrag=0.0):
        
        self.radius_m = radius_m
        self.diameter_m = 2 * radius_m
        self.radius_px = round(g.env.px_from_m(self.radius_m))

        self.density_kgpm2 = density_kgpm2    # mass per unit area
        self.mass_kg = self.density_kgpm2 * math.pi * self.radius_m ** 2
        self.c_drag = c_drag
        
        self.coef_rest = coef_rest
        self.coef_rest_atBirth = coef_rest
        self.CR_fixed = CR_fixed

        # For a Box2d puck.
        self.width_m = None
        self.height_m = None
        self.friction = friction
        self.friction_atBirth = friction
        self.friction_fixed = friction_fixed

        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_mps
        
        # Box2d puck
        self.showSpoke = showSpoke
        self.angle_r = angle_r
        self.angularVelocity_rps = angularVelocity_rps
        self.groupIndex = groupIndex
        
        self.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        self.jet_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        self.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        self.puckDrag_force_2d_N = Vec2D(0.0,0.0)

        self.impulse_2d_Ns = Vec2D(0.0,0.0)
        
        self.selected = False
        
        # For a Box2d puck.
        self.rotation_speed = 0.0
        self.c_angularDrag = c_angularDrag
        self.cursorString_torque_force_Nm = 0

        # Non-center of mass (COM).  #b2d
        # This is a list of dictionaries: each dictionary contains a force and a body location
        self.nonCOM_N = []
        
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
        self.birth_time_s = g.air_table.time_s
        self.age_limit_s = age_limit_s
        
        # Keep track of health.
        self.bullet_hit_count = 0
        self.bullet_hit_limit = hit_limit
        
        # For a Box2d puck.
        self.hw_ratio = hw_ratio # height to width ratio
        self.rect_fixture = rect_fixture
        self.awake = awake

        self.b2d_body = None

        self.pin = pin
        # Add puck to the lists of pucks, controlled pucks, and target pucks.
        if not pin:
            if (g.air_table.engine == 'box2d'):
                self.b2d_body = self.create_Box2d_Puck()
                g.air_table.puck_dictionary[self.b2d_body] = self

            g.air_table.pucks.append(self)
            
            if not self.bullet:
                g.air_table.target_pucks.append(self)
                if self.client_name:
                    g.air_table.controlled_pucks.append(self)
                
    # If you print an object instance...
    def __str__(self):
        return f"puck: x is {self.pos_2d_m.x}, y is {self.pos_2d_m.y}"
    
    # Box2d
    def create_Box2d_Puck(self):
        # Create a dynamic body
        dynamic_body = g.air_table.b2d_world.CreateDynamicBody(
            position=b2Vec2(self.pos_2d_m.tuple()), 
            angle=self.angle_r, angularVelocity=self.angularVelocity_rps,
            linearVelocity=b2Vec2(self.vel_2d_mps.tuple()),
            awake=self.awake
        )
        
        if self.rect_fixture:
            # And add a box fixture onto it.
            half_width_m = self.radius_m
            half_height_m = half_width_m * self.hw_ratio
            self.width_m = half_width_m * 2.0
            self.height_m = half_height_m * 2.0
            dynamic_body.CreatePolygonFixture(
                box=(half_width_m, half_height_m), 
                density=self.density_kgpm2, 
                friction=self.friction_atBirth, restitution=self.coef_rest_atBirth
            )
        else:
            # And add a circular fixture onto it.
            dynamic_body.CreateCircleFixture(
                radius=self.radius_m, 
                density=self.density_kgpm2, 
                friction=self.friction_atBirth, restitution=self.coef_rest_atBirth
            )

        dynamic_body.fixtures[0].filterData.groupIndex = self.groupIndex

        # Set the mass attribute based on what box2d calculates.
        self.mass_kg = dynamic_body.mass
        
        # fluid drag inside Box2D
        dynamic_body.linearDamping = self.c_drag
        dynamic_body.angularDamping = self.c_angularDrag
        dynamic_body.bullet = self.bullet

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
    
    def set_pos_and_vel(self, pos_2d_m, vel_2d_m=Vec2D(0,0)):
        # Update our vectors
        self.pos_2d_m = pos_2d_m
        self.vel_2d_mps = vel_2d_m

        if (g.air_table.engine == 'box2d'):
            # Update Box2D body
            self.b2d_body.position = b2Vec2(pos_2d_m.x, pos_2d_m.y)
            self.b2d_body.linearVelocity = b2Vec2(vel_2d_m.x, vel_2d_m.y)

    def delete(self):
        if (g.air_table.engine == 'box2d'):
            # Remove the puck from the dictionary.
            del g.air_table.puck_dictionary[self.b2d_body]
            # Remove the puck from the world in box2d.
            g.air_table.b2d_world.DestroyBody(self.b2d_body)

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
            if self in g.air_table.target_pucks:
                g.air_table.target_pucks.remove(self)
        
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
            
        # Just after a hit, fill the whole circle with RED (i.e., thickness = 0).
        if self.hit:
            puck_border_thickness = 0
            puck_color = THECOLORS["red"]
            self.hitflash_duration_timer_s += g.env.dt_render_limit_s
            if self.hitflash_duration_timer_s > self.hitflash_duration_timer_limit_s:
                self.hit = False
        else:
            puck_border_thickness = self.border_thickness_px
            if (tempColor != None):
                puck_color = tempColor
            else:    
                puck_color = self.color
        
        if self.rect_fixture:
            # Box2d
            fixture_shape = self.b2d_body.fixtures[0].shape
            vertices_screen_2d_px = []
            for vertex_object_2d_m in fixture_shape.vertices:
                vertex_world_2d_m = self.b2d_body.transform * vertex_object_2d_m  # Overload operation
                vertex_screen_2d_px = g.env.ConvertWorldToScreen( Vec2D(vertex_world_2d_m.x, vertex_world_2d_m.y)) # This returns a tuple
                vertices_screen_2d_px.append( vertex_screen_2d_px) # Append to the list.
            pygame.draw.polygon(g.game_window.surface, puck_color, vertices_screen_2d_px, g.env.zoomLineThickness(puck_border_thickness))
            
        else:
            # Draw main puck body.
            pygame.draw.circle( g.game_window.surface, puck_color, self.pos_2d_px, self.radius_px, g.env.zoomLineThickness(puck_border_thickness))
            
            if (g.air_table.engine == 'box2d' and not self.pin):
                # If it's not a bullet and not a rectangle, draw a spoke to indicate rotational orientation.
                if ((self.bullet == False) and (self.rect_fixture==False) and self.showSpoke):
                    # Shorten the spoke by a fraction of the thickness so that its end
                    # (and the blocky rendering) is hidden in the border.
                    reduction_m = g.env.px_to_m * self.border_thickness_px * 0.50
                    # Position the outer-edge point right from the center (r_m, 0), so
                    # spoke will look like it's at zero angle.
                    point_on_radius_b2d_m = self.b2d_body.GetWorldPoint( b2Vec2(self.radius_m - reduction_m, 0.0))
                    point_on_radius_2d_m = Vec2D( point_on_radius_b2d_m.x, point_on_radius_b2d_m.y)
                    point_on_radius_2d_px = g.env.ConvertWorldToScreen( point_on_radius_2d_m)
                    
                    point_at_center_b2d_m = self.b2d_body.GetWorldPoint( b2Vec2(0.0, 0.0))
                    point_at_center_2d_m = Vec2D( point_at_center_b2d_m.x, point_at_center_b2d_m.y)
                    point_at_center_2d_px = g.env.ConvertWorldToScreen( point_at_center_2d_m)

                    pygame.draw.line(g.game_window.surface, puck_color, point_on_radius_2d_px, point_at_center_2d_px, g.env.zoomLineThickness(puck_border_thickness))
                    # Round the end of the spoke that is at the center of the puck.
                    #pygame.draw.circle( g.game_window.surface, puck_color, self.pos_2d_px, 0.7 *g.env.zoomLineThickness(puck_border_thickness), 0)
        
        # Draw life (poor health) indicator circle.
        if (not self.bullet and self.show_health):
            spent_fraction = float(self.bullet_hit_count) / float(self.bullet_hit_limit)
            
            if self.rect_fixture:
                life_radius_px = spent_fraction * self.radius_px * self.hw_ratio
            else:
                life_radius_px = spent_fraction * self.radius_px
            
            if (life_radius_px < 2.0):
                life_radius_px = 2.0
            
            pygame.draw.circle(g.game_window.surface, THECOLORS["red"], self.pos_2d_px, life_radius_px, g.env.zoomLineThickness(2))


class RotatingTube:
    def __init__(self, puck, sf_abs=False):
        # Associate the tube with the puck.
        self.puck = puck
    
        self.color = g.env.clients[self.puck.client_name].cursor_color
        
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
            vertices_2d_px.append( g.env.ConvertWorldToScreen(vertex_2d_m + base_point_2d_m))
        return vertices_2d_px
        
    def draw_tube(self, line_thickness=3):
        # Draw the tube on the game-window surface. Establish the base_point as the center
        # of the puck.
        pygame.draw.polygon(g.game_window.surface, self.color, 
                            self.convert_from_world_to_screen(self.tube_vertices_2d_m, self.puck.pos_2d_m), g.env.zoomLineThickness(line_thickness))


class Jet(RotatingTube):
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
        self.jet_force_N = 1.3 * self.puck.mass_kg * abs(g.air_table.gON_2d_mps2.y)
        
        # Point everything down for starters.
        self.rotate_everything( 180)
        
        self.client = g.env.clients[self.puck.client_name]
        
    def turn_jet_forces_onoff(self):
        if (self.client.key_w == "D"):
            # Force on puck is in the opposite direction of the jet tube.
            self.puck.jet_force_2d_N = self.direction_2d_m * (-1) * self.jet_force_N
        else:    
            self.puck.jet_force_2d_N = self.direction_2d_m * 0.0
            
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
                                

class Gun( RotatingTube):
    def __init__(self, puck, sf_abs=True, bullet_age_limit_s=3.0):
        # Associate the gun with the puck (referenced in the RotatingTube class).
        super().__init__(puck, sf_abs=sf_abs)
        
        # Degrees of rotation per second.
        self.rotation_rate_dps = 180.0
        
        self.color = g.env.clients[self.puck.client_name].cursor_color

        # Set a negative group index for bullet stream (inhibit collisions with itself)
        if self.puck.client_name == "local":
            self.groupIndex = -100
        else:
            self.groupIndex = -int(self.puck.client_name[1:])

        # Run this method of the RotationTube class to set the initial angle of each new gun.
        self.rotate_everything( 45)
        
        self.bullet_speed_mps = 5.0
        self.fire_time_s = g.air_table.time_s
        self.firing_delay_s = 0.1
        self.bullet_count = 0
        self.bullet_count_limit = 10
        self.bullet_age_limit_s = bullet_age_limit_s
        self.gun_recharge_wait_s = 2.5
        self.gun_recharge_start_time_s = g.air_table.time_s
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
        self.shield_recharge_start_time_s = g.air_table.time_s
        self.shield_thickness = 5
        self.targetPuck = None
        self.client = g.env.clients[self.puck.client_name]
        
    def client_rotation_control(self):
        if (self.client.key_j == "D"):
            self.rotate_everything( +self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_l == "D"):
            self.rotate_everything( -self.rotation_rate_dps * g.env.dt_render_limit_s)
        if (self.client.key_k == "D"):
            # Rotate jet tube to be in the same direction as the motion of the puck.
            puck_velocity_angle = self.puck.vel_2d_mps.get_angle()
            current_gun_angle = self.direction_2d_m.get_angle()
            self.rotate_everything(puck_velocity_angle - current_gun_angle)
            
            # Reset this so it doesn't keep flipping. Just want it to flip the direction
            # once but not keep flipping. This first line is enough to keep the local
            # client from flipping again because the local keyboard doesn't keep sending
            # the "D" event if the key is held down.
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
        puck_indexes = list( range( len( g.air_table.target_pucks)))
        # Shuffle them.
        random.shuffle( puck_indexes)
        
        for puck_index in puck_indexes:
            puck = g.air_table.target_pucks[ puck_index]
            # Other than itself, pick a new target.
            if (puck != self.puck) and (puck != self.targetPuck):
                self.targetPuck = puck
                break
        
    def control_firing(self):
        droneShooting = self.client.drone and (len(g.air_table.target_pucks) > 1)
        
        # Fire only if the shield is off.
        if ((self.client.key_i == "D") and (not self.shield)) or droneShooting:
            # Fire the gun.
            if ((g.air_table.time_s - self.fire_time_s) > self.firing_delay_s) and (not self.gun_recharging):
                self.fire_gun()
                self.bullet_count += 1
                # Timestamp the firing event.
                self.fire_time_s = g.air_table.time_s
    
        # Check to see if gun bullet count indicates the need to start recharging.
        if (self.bullet_count > self.bullet_count_limit):
            self.gun_recharge_start_time_s = g.air_table.time_s
            self.gun_recharging = True
            self.bullet_count = 0
            # At the beginning of the charging period, find a new target. This gives a
            # human player an indication of what the drone is targeting. And since this is
            # at the beginning of the gun charging period, it gives the player some time
            # for evasive maneuvers.
            if self.client.drone:
                self.findNewTarget()
    
        # If recharged.
        if (self.gun_recharging and (g.air_table.time_s - self.gun_recharge_start_time_s) > self.gun_recharge_wait_s):
            self.gun_recharging = False
            # If the puck the drone is aiming at has been destroyed, find a new target
            # before starting to shoot.
            if self.client.drone and not (self.targetPuck in g.air_table.target_pucks):
                self.findNewTarget()
                
    def fire_gun(self):
        bullet_radius_m = 0.05
        # Set the initial position of the bullet so that it clears (doesn't collide with)
        # the host puck.
        initial_position_2d_m = (self.puck.pos_2d_m +
                                (self.direction_2d_m * (1.1 * self.puck.radius_m + 1.1 * bullet_radius_m)) )
        
        # Relative velocity of the bullet: the bullet velocity as seen from the host puck.
        # This is the speed of the bullet relative to the motion of the host puck (host
        # velocity BEFORE the firing of the bullet).
        bullet_relative_vel_2d_mps = self.direction_2d_m * self.bullet_speed_mps
        
        # Absolute velocity of the bullet
        bullet_absolute_vel_2d_mps = self.puck.vel_2d_mps + bullet_relative_vel_2d_mps

        temp_bullet = Puck(initial_position_2d_m, bullet_radius_m, 0.3, vel_2d_mps=bullet_absolute_vel_2d_mps, 
                           bullet=True, age_limit_s=self.bullet_age_limit_s, groupIndex=self.groupIndex)
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
            self.shield_recharge_start_time_s = g.air_table.time_s
            self.shield = False
            self.shield_recharging = True
            self.shield_hit_count = 0
        else:
            self.shield_thickness = g.env.zoomLineThickness(5 * (1 - self.shield_hit_count/self.shield_hit_count_limit), noFill=True)
        
        # If recharged.
        if (self.shield_recharging and (g.air_table.time_s - self.shield_recharge_start_time_s) > self.shield_recharge_wait_s):
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
                self.shield_hit_duration_s += g.env.dt_render_limit_s
                if (self.shield_hit_duration_s > self.shield_hit_duration_limit_s):
                    self.shield_hit = False
                    
            else:
                # Display the shield 5px outside of the puck.
                shield_radius_px = self.puck.radius_px + round(5 * g.env.viewZoom)
                pygame.draw.circle(g.game_window.surface, self.color, 
                                   self.puck.pos_2d_px, shield_radius_px, self.shield_thickness)
                                   
                                   
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
