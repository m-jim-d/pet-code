#!/usr/bin/env python3

# Filename: A10_m_air_table.py

"""
Modeling of 2D physics.

This module provides the potential for different air-table implementations for 2D physics
simulations, including basic collisions with circular objects, perfect-kiss collisions,
and Box2D-based physics. Features include:

Classes:
    AirTable: Core simulation features including gravity, pucks, and springs
    CircularAirTable: Basic collision detection and resolution for circular pucks

Each table type supports puck and spring objects, and customizable physics parameters for
different simulation needs.
"""

import threading, time, math, importlib

import pygame
from pygame.color import THECOLORS

# Vector class
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A10_m_globals as g


class AirTable:
    def __init__(self, walls_dic, version="10"):
        # Dynamic import from Axx_m_air_table_objects.py
        objects = importlib.import_module(f'A{version}_m_air_table_objects')
        self.Puck = objects.Puck
        self.Spring = objects.Spring
        
        self.gON_2d_mps2 = Vec2D(-0.0, -9.8)
        self.gOFF_2d_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_2d_mps2
        self.g_ON = False
        
        # For pucks that don't have fixed restitutions, this sets a limit for their
        # restitution when gravity is toggled on.
        self.gON_coef_rest_max = 0.85
        
        self.pucks = []
        self.raw_tubes = []
        self.controlled_pucks = []
        
        self.springs = []
        
        self.walls_dic_atBirth = walls_dic.copy()
        self.walls_dic = walls_dic.copy()
        
        self.collision_count = 0
        self.coef_rest = 1.0

        self.stop_physics = False
        self.tangled = False
        
        self.inhibit_wall_collisions = False
        self.inhibit_all_puck_collisions = False
        self.correct_for_wall_penetration = True
        self.correct_for_puck_penetration = True
        
        # Time step (established in game loop)
        self.dt_s = None
        # General clock time for determining bullet age.
        self.time_s = 0.0

        self.FPS_display = True
        self.engine = "not yet established"

        self.delayed_throw = None

    def resetFence(self):
        self.walls_dic = self.walls_dic_atBirth.copy()

    def makeSquareFence(self):
        # Make a square fence.
        xy_diff_m = (g.env.length_x_m - (g.env.length_x_m / g.env.aspect_ratio_wh))
        self.walls_dic['L_m'] = 0 + (xy_diff_m / 2.0)
        self.walls_dic['R_m'] = g.env.length_x_m - (xy_diff_m / 2.0)

    def throw_puck(self, puck, velocity_2d_mps, delay_s=1.0):
        def throw_it_later():
            time.sleep(delay_s)
            if puck in self.pucks:
                puck.set_pos_and_vel(puck.pos_2d_m, velocity_2d_mps)
        
        # This thread is removed at the start of the next demo in make_some_pucks.
        self.delayed_throw = threading.Thread(daemon=True, target=throw_it_later)
        self.delayed_throw.start()
                
    def pinnedPuck(self, puck_position_2d_m, radius_m=1.5, density=1.0, angle_d=0,
                         pin_position_2d_m=None, strength_Npm=200.0):

        if not pin_position_2d_m:
            pin_position_2d_m = puck_position_2d_m

        p1 = self.Puck(puck_position_2d_m, radius_m, density,
            color=THECOLORS["coral"],
            friction=1.0, friction_fixed=True,
            coef_rest=0.0, CR_fixed=True, border_px=5, 
            angle_r=g.env.radians(angle_d)
        )
        self.Spring(p1, pin_position_2d_m, color=THECOLORS['dodgerblue'],
            strength_Npm=strength_Npm, width_m=0.03, c_drag=15.0, c_damp=15.0
        )
            
    def draw(self):
        if not self.inhibit_wall_collisions:
            #{"L_m":0.0, "R_m":10.0, "B_m":0.0, "T_m":10.0}
            topLeft_2d_px =   g.env.ConvertWorldToScreen( Vec2D( self.walls_dic['L_m'],        self.walls_dic['T_m']))
            topRight_2d_px =  g.env.ConvertWorldToScreen( Vec2D( self.walls_dic['R_m']-0.01,   self.walls_dic['T_m']))
            botLeft_2d_px =   g.env.ConvertWorldToScreen( Vec2D( self.walls_dic['L_m'],        self.walls_dic['B_m']+0.01))
            botRight_2d_px =  g.env.ConvertWorldToScreen( Vec2D( self.walls_dic['R_m']-0.01,   self.walls_dic['B_m']+0.01))
            
            pygame.draw.line(g.game_window.surface, THECOLORS["orangered1"], topLeft_2d_px,  topRight_2d_px, 1)
            pygame.draw.line(g.game_window.surface, THECOLORS["orangered1"], topRight_2d_px, botRight_2d_px, 1)
            pygame.draw.line(g.game_window.surface, THECOLORS["orangered1"], botRight_2d_px, botLeft_2d_px,  1)
            pygame.draw.line(g.game_window.surface, THECOLORS["orangered1"], botLeft_2d_px,  topLeft_2d_px,  1)
    
    def checkForPuckAtThisPosition(self, x_px_or_tuple, y_px = None):
        if y_px == None:
            self.x_px = x_px_or_tuple[0]
            self.y_px = x_px_or_tuple[1]
        else:
            self.x_px = x_px_or_tuple
            self.y_px = y_px
        
        test_position_m = g.env.ConvertScreenToWorld(Vec2D(self.x_px, self.y_px))
        for puck in self.pucks:
            vector_difference_m = test_position_m - puck.pos_2d_m
            # Use squared lengths for speed (avoid square root)
            mag_of_difference_m2 = vector_difference_m.length_squared()
            if mag_of_difference_m2 < puck.radius_m**2:
                puck.selected = True
                return puck
        return None

    def update_TotalForce_Speed_Position(self, puck):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/self.dt_s)
        
        # Acceleration from Newton's law.
        acc_2d_mps2 = puck_forces_2d_N / puck.mass_kg
        
        # Limit the absolute value of the acceleration components.
        limit_mps2 = 1000.0  # m/s^2
        acc_2d_mps2 = Vec2D(min(max(acc_2d_mps2.x, -limit_mps2), limit_mps2),
                            min(max(acc_2d_mps2.y, -limit_mps2), limit_mps2))
        
        # Acceleration changes the velocity:  dv = a * dt
        # Velocity at the end of the timestep.
        puck.vel_2d_mps = puck.vel_2d_mps + (acc_2d_mps2 * self.dt_s)
        
        # Calculate the new physical puck position using the average velocity.
        # Velocity changes the position:  dx = v * dt
        puck.pos_2d_m = puck.pos_2d_m + (puck.vel_2d_mps * self.dt_s)
        
        # Now reset the aggregate forces.
        puck.SprDamp_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_spring_force_2d_N = Vec2D(0.0,0.0)
        puck.cursorString_puckDrag_force_2d_N = Vec2D(0.0,0.0)
        puck.impulse_2d_Ns = Vec2D(0.0,0.0)


class CircularAirTable(AirTable):
    def __init__(self, walls_dic, version="10"):
        super().__init__(walls_dic, version=version)

        self.engine = "circular"

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

    def checkForFenceCollisions(self, puck):
        if (((puck.pos_2d_m.y - puck.radius_m) < self.walls_dic["B_m"]) or ((puck.pos_2d_m.y + puck.radius_m) > self.walls_dic["T_m"])):
            
            if self.correct_for_wall_penetration:
                if (puck.pos_2d_m.y - puck.radius_m) < self.walls_dic["B_m"]:
                    penetration_y_m = self.walls_dic["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                    puck.pos_2d_m.y += 2 * penetration_y_m
            
                if (puck.pos_2d_m.y + puck.radius_m) > self.walls_dic["T_m"]:
                    penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls_dic["T_m"]
                    puck.pos_2d_m.y -= 2 * penetration_y_m
            
            puck.vel_2d_mps.y *= -1 * min(self.coef_rest, puck.coef_rest)
        
        if (((puck.pos_2d_m.x - puck.radius_m) < self.walls_dic["L_m"]) or ((puck.pos_2d_m.x + puck.radius_m) > self.walls_dic["R_m"])):
            
            if self.correct_for_wall_penetration:
                if (puck.pos_2d_m.x - puck.radius_m) < self.walls_dic["L_m"]:
                    penetration_x_m = self.walls_dic["L_m"] - (puck.pos_2d_m.x - puck.radius_m)
                    puck.pos_2d_m.x += 2 * penetration_x_m
            
                if (puck.pos_2d_m.x + puck.radius_m) > self.walls_dic["R_m"]:
                    penetration_x_m = (puck.pos_2d_m.x + puck.radius_m) - self.walls_dic["R_m"]
                    puck.pos_2d_m.x -= 2 * penetration_x_m
                    
            #print("CR x wall, puck:", self.coef_rest, puck.coef_rest)                    
            puck.vel_2d_mps.x *= -1 * min(self.coef_rest, puck.coef_rest)

    def check_for_puck_collisions(self, puck, otherpuck):
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
        
            # Ignore collisions within same negative group
            if (puck.groupIndex == otherpuck.groupIndex) and (puck.groupIndex < 0):
                return

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

    def check_for_collisions(self):
        self.tangled = False

        # Collisions with the perimeter fence (walls)
        for i, puck in enumerate(self.pucks):
            if not self.inhibit_wall_collisions:
                self.checkForFenceCollisions(puck)

            # Collisions with other pucks
            if not self.inhibit_all_puck_collisions:
                for otherpuck in self.pucks[i+1:]:
                    self.check_for_puck_collisions(puck, otherpuck)