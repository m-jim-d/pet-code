#!/usr/bin/env python3

# Filename: A15_air_table.py

"""
Modeling of 2D physics.

This module provides different air-table implementations for 2D physics simulations,
including basic collisions with circular objects, perfect-kiss collisions, and Box2D-based
physics. Features include:

Classes:
    AirTable: Core simulation features including gravity, pucks, and springs
    CircularAirTable: Basic collision detection and resolution for circular pucks
    PerfectKissAirTable: Precise collision handling for perfect elastic collisions
    Box2DAirTable: Advanced simulation of non-circular objects using the Box2D engine

Each table type supports puck and spring objects, and customizable physics parameters
for different simulation needs.
"""

import random

from typing import Union, Tuple

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D

# Global variables shared across scripts
import A15_globals as g
from A15_air_table_objects import Wall, Puck, Spring, Gun, Jet

from Box2D import (b2World, b2Vec2, b2_dynamicBody, b2AABB, b2QueryCallback, b2ContactListener)


class AirTable:
    def __init__(self, walls_dic):
        self.gON_2d_mps2 = Vec2D(-0.0, -9.8)
        self.gOFF_2d_mps2 = Vec2D(-0.0, -0.0)
        self.g_2d_mps2 = self.gOFF_2d_mps2
        self.g_ON = False
        
        self.pucks = []
        self.controlled_pucks = []
        self.target_pucks = []
        
        self.springs = []
        
        self.walls_dic = walls_dic
        
        self.collision_count = 0
        self.coef_rest = 1.0

        self.stop_physics = False
        self.tangled = False
        
        self.inhibit_wall_collisions = False
        self.correct_for_wall_penetration = True
        self.correct_for_puck_penetration = True
        
        # Time step (established in game loop)
        self.dt_s = None
        # General clock time for determining bullet age.
        self.time_s = 0.0
        # Timer for the Jello Madness game.
        self.game_time_s = 0.0

        self.FPS_display = True
        self.engine = "not yet established"

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

        # Create a grid of pucks. Starting at the initial position, populate a column of pucks, increasing the y position.
        # Then reset the y position and increase the x position, adding additional columns. k ranges over each puck in a column.
        # j ranges over the columns.

        for j in range(grid_x_n):
            for k in range(grid_y_n):
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
                      coef_rest=coef_rest, CR_fixed=True, c_angularDrag=0.5)
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
                Spring( self.pucks[o_index], self.pucks[o_index+1], spring_length_m, spring_strength_Npm2, 
                        color=THECOLORS["blue"], c_damp=spring_damping)
        
        # Springs connected on diagonals (springs are longer).
        spring_length_m = 1.2 * 2**0.5

        for m in range(0,grid_x_n-1):
            for n in range(1,grid_y_n):
                o_index = n + (m * (grid_y_n))
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
            if (self.engine == 'box2d'): puck.b2d_body.linearVelocity = velocity_2d_mps.tuple()

        return {'angle':angleOfGrid, 'speed_mps':speed_mps}

    def throwJello_variations(self):
        initial_states = [
            {'x_n':4, 'y_n':3, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':4, 'y_n':2, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':4, 'y_n':4, 'ang_min':-10, 'ang_max':55, 'spd_min': 0,'spd_max': 90},
            {'x_n':5, 'y_n':3, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':5, 'y_n':2, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':6, 'y_n':2, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':3, 'y_n':3, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':3, 'y_n':2, 'ang_min':-10, 'ang_max':90, 'spd_min':10,'spd_max': 40},
            {'x_n':2, 'y_n':2, 'ang_min':-10, 'ang_max':90, 'spd_min': 0,'spd_max':200}
        ]
        g.env.demo_variations[8]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[8]['index']]

        self.game_time_s = 0
        self.jello_tangle_checking_enabled = True
        throw = self.buildJelloGrid( 
            angle=(state['ang_min'], state['ang_max']), 
            speed=(state['spd_min'], state['spd_max']),
            pos_initial_2d_m=Vec2D(3.0, 1.0), 
            grid_x_n=state['x_n'], grid_y_n=state['y_n']
        )

        g.game_window.update_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[8]['index'] + 1}" +
            f"     grid = ({state['x_n']}, {state['y_n']})" +
            f"  angle = {throw['angle']:.1f}  speed = {throw['speed_mps']:.1f}"
        )

    """
    The following methods are used (only) by the circular versions of the air table (Circular and PerfectKiss).
    """
    def draw(self):
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

    """
    Note that update_PuckSpeedAndPosition has a corresponding update_TotalForceVectorOnPuck method 
    in the Box2DAirTable class (speed and position calculated by Box2D). 
    """
    def update_PuckSpeedAndPosition(self, puck):
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
        if not self.inhibit_wall_collisions:
            if (((puck.pos_2d_m.y - puck.radius_m) < self.walls_dic["B_m"]) or ((puck.pos_2d_m.y + puck.radius_m) > self.walls_dic["T_m"])):
                
                if self.correct_for_wall_penetration:
                    if (puck.pos_2d_m.y - puck.radius_m) < self.walls_dic["B_m"]:
                        penetration_y_m = self.walls_dic["B_m"] - (puck.pos_2d_m.y - puck.radius_m)
                        puck.pos_2d_m.y += 2 * penetration_y_m
                
                    if (puck.pos_2d_m.y + puck.radius_m) > self.walls_dic["T_m"]:
                        penetration_y_m = (puck.pos_2d_m.y + puck.radius_m) - self.walls_dic["T_m"]
                        puck.pos_2d_m.y -= 2 * penetration_y_m
                
                puck.vel_2d_mps.y *= -1 * min(self.coef_rest, puck.coef_rest)
                if (self.engine == "circular-perfectKiss") and self.perfect_kiss: self.collision_count += 1 * self.count_direction
            
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
                if (self.engine == "circular-perfectKiss") and self.perfect_kiss: self.collision_count += 1 * self.count_direction


class CircularAirTable(AirTable):
    def __init__(self, walls_dic):
        super().__init__(walls_dic)

        self.engine = "circular"

    def check_for_collisions(self):
        self.tangled = False

        for i, puck in enumerate(self.pucks):
            # Check for collisions in the perimeter fence (walls)
            self.checkForFenceCollisions(puck)

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


class PerfectKissAirTable(AirTable):
    def __init__(self, walls_dic):
        super().__init__(walls_dic)

        self.engine = "circular-perfectKiss"

        # For perfect kiss
        self.perfect_kiss = False
        self.count_direction = 1
        self.timeDirection = 1

    def time_past_kiss(self, puckA, puckB):
        # Determine the time between the kiss point and collision detection event (penetration time).
        
        initial_collision_angle = (puckA.pos_2d_m - puckB.pos_2d_m).get_angle_between(Vec2D(1.0,0.0))
        
        # As seen from B.
        puckA_relvel_2d_mps = puckA.vel_2d_mps - puckB.vel_2d_mps
        
        # Previous position vectors (position 1) of the two pucks
        puckA_1_pos_2d_m = puckA.pos_2d_m - puckA.vel_2d_mps * self.dt_s
        puckB_1_pos_2d_m = puckB.pos_2d_m - puckB.vel_2d_mps * self.dt_s
        
        # Position vector 2-prime of PuckA
        puckA_2p_pos_2d_m = puckA_1_pos_2d_m + puckA_relvel_2d_mps * self.dt_s
        
        # Prime path vectors
        prime_path_puckA_2d_m = puckA_2p_pos_2d_m - puckA_1_pos_2d_m
        prime_normalized_2d_m = prime_path_puckA_2d_m.normal()
        
        # Vector between the original positions of the two pucks.
        A1_B1_path_2d_m = puckB_1_pos_2d_m - puckA_1_pos_2d_m
        
        # Projection of A1_B1_path_2d_m onto the prime vector.
        A1_B1_projection_2d_m = A1_B1_path_2d_m.projection_onto( prime_path_puckA_2d_m)
        
        # B1 to prime path vector (vector to nearest point on prime path). The difference
        # between the B_1 vector and its projection onto the prime vector.
        B1_to_prime_2d_m = A1_B1_path_2d_m - A1_B1_projection_2d_m
        
        # Distance x (scaler). Distance between near point on prime and the A2K (kiss location of A2).
        x_m = ((puckA.radius_m + puckB.radius_m)**2 - B1_to_prime_2d_m.length_squared())**0.5
        x_2d_m = prime_normalized_2d_m * x_m
        
        # Kiss point vector
        puckA_2_kiss_2d_m = puckA_1_pos_2d_m + A1_B1_projection_2d_m - x_2d_m
        
        # Vector between detection and kiss.
        d_2d_m = puckA_2p_pos_2d_m - puckA_2_kiss_2d_m
        
        # Time between detection and kiss. Avoid zero in the denominator.
        if puckA_relvel_2d_mps.x > 0:
            time_between_kiss_and_detection_s = d_2d_m.x / puckA_relvel_2d_mps.x
        else:
            time_between_kiss_and_detection_s = d_2d_m.y / puckA_relvel_2d_mps.y
            
        return time_between_kiss_and_detection_s

    def check_for_collisions(self):
        self.tangled = False

        for i, puck in enumerate(self.pucks):
            # Check for collisions in the perimeter fence (walls)
            self.checkForFenceCollisions(puck)

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
                    if self.perfect_kiss: self.collision_count += 1 * self.count_direction
                    
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
                    
                    # Draw the overlapping pucks.
                    if self.perfect_kiss: puck.draw(tempColor=THECOLORS["red"]); otherpuck.draw(tempColor=THECOLORS["red"])

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
                        if self.perfect_kiss:
                            # Use a special perfect-kiss method to determine the time.
                            penetration_time_s = self.time_past_kiss(puck, otherpuck)
                        else:    
                            penetration_time_s = penetration_m / relative_normal_spd_mps
                                                    
                        penetration_time_scaler = 1.0  # This can be useful for testing to amplify and see the correction.
                        
                        # First, reverse the two pucks, to their collision point, along their incoming trajectory paths.
                        if self.perfect_kiss:
                            puck.pos_2d_m = puck.pos_2d_m - (puck.vel_2d_mps * (penetration_time_scaler * penetration_time_s))
                            otherpuck.pos_2d_m = otherpuck.pos_2d_m - (otherpuck.vel_2d_mps * (penetration_time_scaler * penetration_time_s))
                            
                            # Draw the perfect-kissing pucks (you'll only be able to see this in the example run that is started by pressing
                            # the 3 key on the number pad (or shift-3). This is one of the pool-shot examples that inhibits screen clears.
                            puck.draw(tempColor=THECOLORS["cyan"])
                            otherpuck.draw(tempColor=THECOLORS["cyan"])
                        
                        else:    
                            puck.pos_2d_m = puck.pos_2d_m - (puck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))
                            otherpuck.pos_2d_m = otherpuck.pos_2d_m - (otherpuck_normal_2d_mps * (penetration_time_scaler * penetration_time_s))
                        
                        if self.perfect_kiss:
                            # Recalculate the tangent and normals based on the pucks in the just-touching position.
                            puck_to_puck_2d_m = otherpuck.pos_2d_m - puck.pos_2d_m
                            tangent_p_to_p_2d_m = Vec2D.rotate90(puck_to_puck_2d_m)
                            # The calculate velocity components along and perpendicular to the normal.
                            puck_normal_2d_mps = puck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                            puck_tangent_2d_mps = puck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                            otherpuck_normal_2d_mps = otherpuck.vel_2d_mps.projection_onto(puck_to_puck_2d_m)
                            otherpuck_tangent_2d_mps = otherpuck.vel_2d_mps.projection_onto(tangent_p_to_p_2d_m)
                        
                        # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restitution).
                        # of 1 here to better avoid stickiness.
                        CR_puck = 1
                        puck_normal_AFTER_mps, otherpuck_normal_AFTER_mps = self.AandB_normal_AFTER_2d_mps( puck_normal_2d_mps, puck.mass_kg, otherpuck_normal_2d_mps, otherpuck.mass_kg, CR_puck)
                                                       
                        # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
                        # This will put the pucks where they should have been at the time of collision detection.
                        if self.perfect_kiss:
                            # Temp values for puck and otherpuck velocities after the collision.
                            puck_vel_2d_mps = puck_normal_AFTER_mps + puck_tangent_2d_mps
                            otherpuck_vel_2d_mps = otherpuck_normal_AFTER_mps + otherpuck_tangent_2d_mps

                            puck.pos_2d_m = puck.pos_2d_m + (puck_vel_2d_mps * (penetration_time_scaler * penetration_time_s))
                            otherpuck.pos_2d_m = otherpuck.pos_2d_m + (otherpuck_vel_2d_mps * (penetration_time_scaler * penetration_time_s))
                        else:
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


"""  fwQueryCallback and myContactListener are dependencies of Box2DAirTable  """

class fwQueryCallback(b2QueryCallback):
    # Box2D checks for objects at particular location (p), e.g. under the cursor.
    def __init__(self, p): 
        super().__init__()
        self.point = p
        self.fixture = None  # Initialize fixture attribute

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


class myContactListener(b2ContactListener):
    def __init__(self, air_table):
        super().__init__()
        self.air_table = air_table

    def BeginContact(self, contact):
        # Check if both bodies are in the puck dictionary
        bodyA = contact.fixtureA.body
        bodyB = contact.fixtureB.body

        if (bodyA in self.air_table.puck_dictionary) and (bodyB in self.air_table.puck_dictionary):
            puckA = self.air_table.puck_dictionary[bodyA]
            puckB = self.air_table.puck_dictionary[bodyB]

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


class Box2DAirTable(AirTable):
    def __init__(self, walls_dic):
        super().__init__(walls_dic)

        self.engine = "box2d"

        self.puck_dictionary = {}
        self.walls = []

        self.jello_tangle_checking_enabled = False
        self.tangle_checker_time_s = 0.0

        # Create the Box2D world
        self.b2d_world = b2World(gravity=(-0.0, -0.0), doSleep=True, contactListener=myContactListener(self))

    def buildFence(self, onoff={'L':True,'R':True,'T':True,'B':True}):
        for eachWall in self.walls[:]:
            if eachWall.fence:
                eachWall.delete()

        width_m = 0.05 # 0.05
        fenceColor = THECOLORS['orangered1']
        border_px = 2
        nudge_m = g.env.px_to_m * 1 # nudge of 1 pixel
        # Left and right walls
        if onoff['L']: Wall( Vec2D( self.walls_dic["L_m"] - (width_m + nudge_m), self.walls_dic["T_m"]/2.0), 
            width_m, self.walls_dic["T_m"]/2.0, fence=True, border_px=border_px, color=fenceColor)
        if onoff['R']: Wall( Vec2D( self.walls_dic["R_m"] + width_m, self.walls_dic["T_m"]/2.0), 
            width_m, self.walls_dic["T_m"]/2.0, fence=True, border_px=border_px, color=fenceColor)
        # Top and bottom walls
        if onoff['T']: Wall( Vec2D( self.walls_dic["R_m"]/2.0, self.walls_dic["T_m"] + (width_m + nudge_m)), 
            self.walls_dic["R_m"]/2.0, width_m, fence=True, border_px=border_px, color=fenceColor)
        if onoff['B']: Wall( Vec2D( self.walls_dic["R_m"]/2.0, self.walls_dic["B_m"] - width_m), 
            self.walls_dic["R_m"]/2.0, width_m, fence=True, border_px=border_px, color=fenceColor)

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
        test_position_2d_m = g.env.ConvertScreenToWorld(Vec2D(self.x_px, self.y_px))
        
        # Convert this to a box2d vector.
        p = b2Vec2( test_position_2d_m.tuple())
        
        # Make a small box.
        aabb = b2AABB( lowerBound=p-(0.001, 0.001), upperBound=p+(0.001, 0.001))

        # Query the world for overlapping shapes.
        query = fwQueryCallback( p)
        self.b2d_world.QueryAABB( query, aabb)
        
        # If the query was successful and found a body at the cursor point.
        if query.fixture:
            selected_b2d_body = query.fixture.body
            selected_b2d_body.awake = True
        
            # Find the local point in the body's coordinate system.
            local_b2d_m = selected_b2d_body.GetLocalPoint( p)
        
            # Use a dictionary to identify the puck based on the b2d body.
            # Bullets have not been added to the dictionary.
            if not selected_b2d_body.bullet:
                selected_puck = self.puck_dictionary[ selected_b2d_body]
                selected_puck.selected = True
        
            # Return a dictionary with the puck and local selection point on it.
            return {'puck': selected_puck, 'b2d_xy_m': local_b2d_m}
        
        else:
            return {'puck': None, 'b2d_xy_m': b2Vec2(0,0)}
    
    def update_TotalForceVectorOnPuck(self, puck):
        # Net resulting force on the puck.
        puck_forces_2d_N = (self.g_2d_mps2 * puck.mass_kg) + (puck.SprDamp_force_2d_N + 
                                                              puck.jet_force_2d_N +
                                                              puck.puckDrag_force_2d_N +
                                                              puck.cursorString_spring_force_2d_N +
                                                              puck.cursorString_puckDrag_force_2d_N +
                                                              puck.impulse_2d_Ns/self.dt_s)
        
        # Apply this force to the puck's center of mass (COM) in the Box2d world.
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
        if self.tangle_checker_time_s > 0.1:
            self.tangle_checker_time_s = 0.0
            
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
