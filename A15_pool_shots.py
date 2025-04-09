#!/usr/bin/env python3

# Filename: A15_pool_shots.py

"""
Pool-shot scenarios for the air table physics simulation.

This module illustrates a pattern for sharing functionality between the _m_ series
(A10-A14) and the final baseline (A15+). It uses runtime detection of the script
name to determine which version is running and automatically selects the appropriate
Puck class and globals module.

This allows us to maintain a single implementation of pool game functions that work
across both versions, avoiding code duplication while preserving compatibility.
"""

import sys, math

from pygame.color import THECOLORS

from A09_vec2d import Vec2D

def get_Puck_and_g():
    """Get the appropriate Puck class and globals based on script name."""
    # sys.argv[0] is the name of the script being run (e.g. 'A15c_2D_perfect_kiss_serverN.py')
    # Check if the 'A15' or 'A16' substrings are in the name to determine which version to use.
    if any(substring in sys.argv[0] for substring in ['A15','A16']):
        import A15_globals as g
        from A15_air_table_objects import Puck
        return Puck, g
    else:
        import A10_m_globals as g
        return g.air_table.Puck, g  # A10 version

def pool_line_of_balls(offset_percent=0):
    Puck, g = get_Puck_and_g()

    g.air_table.inhibit_wall_collisions = True
    
    density = 1.0
    radius_m = 0.1
    
    # A group of n target pucks at the same y position but separated by a gap.
    n_targets = 20
    gap_m = radius_m * 1.50
    # Start group of targets at 3 puck diameters from the right edge.
    right_edge_x = g.game_window.UR_2d_m.x
    pos_first_target = Vec2D(right_edge_x - 3 * (2 * radius_m), g.game_window.center_2d_m.y)
    pos_x_2d_m = pos_first_target.copy()
    for i in range(n_targets):
        pos_x_2d_m -= Vec2D(2 * radius_m + gap_m, 0)
        Puck(pos_x_2d_m, radius_m, density,
                coef_rest=1.0, CR_fixed=True,
                bullet=True, color=THECOLORS['gold'], border_px=0)

    # Position the cue ball at the right edge of the screen slightly offset in the
    # y direction.
    y_offset_m = radius_m * offset_percent / 100.0
    print(f"y_offset_m = {y_offset_m} ({offset_percent}%)")
    p1_init_pos_2d_m = Vec2D(right_edge_x - radius_m, g.game_window.center_2d_m.y + y_offset_m)
    p1 = Puck(p1_init_pos_2d_m, radius_m, density,
                coef_rest=1.0, CR_fixed=True,
                bullet=True, color=THECOLORS['royalblue'], border_px=0)
    
    g.air_table.throw_puck(p1, Vec2D(-1, 0) * 5.0, delay_s=1.0)

def pool_trick_shot():
    Puck, g = get_Puck_and_g()

    puck_parms = {
        'border_px': 0,
        'coef_rest': 1.0,
        'CR_fixed': True
    }

    if g.air_table.engine == 'box2d':
        g.air_table.buildFence(onoff={'L':False,'R':False,'T':False,'B':False}) # no fence:
        puck_parms['friction'] = 0
        puck_parms['friction_fixed'] = True
        puck_parms['angularVelocity_rps'] = 0
    else:
        g.air_table.inhibit_wall_collisions = True
    
    density = 1.0

    n_pucks = 15
    radius_m = 0.4

    # The polygon radius is the distance from the center of the polygon to any of its
    # vertices. This formula calculates the radius so that the sides of the polygon are
    # equal to twice the puck radius. If pucks are positioned on the vertices they will
    # just be touching.
    polygon_radius_m = radius_m / math.sin(math.pi/n_pucks)

    # Place the pucks a little farther out than their touching point.
    little_extra_m = 0.3
    center_to_puck_2d_m = Vec2D(0.0, polygon_radius_m + little_extra_m)
    for i in range(0, n_pucks-2):
        angle = (360 / n_pucks) * i

        rotated_c_to_puck_2d_m = center_to_puck_2d_m.rotated(angle)
        puck_position_2d_m = g.game_window.center_2d_m + rotated_c_to_puck_2d_m

        Puck(puck_position_2d_m, radius_m, density, color=THECOLORS['darkkhaki'], **puck_parms)

    # This cue-ball puck will be automatically shot or flung or by the user at the target pucks.
    cueBall_density = density
    cueBall_r_m = radius_m
    # To the right of the first puck.
    cB_init_pos_2d_m = g.air_table.pucks[0].pos_2d_m + Vec2D(4.0, 0.0)
    p1 = Puck(cB_init_pos_2d_m, cueBall_r_m, cueBall_density, color=THECOLORS['royalblue'],
              bullet=True, **puck_parms)
    
    g.air_table.throw_puck(p1, Vec2D(-1, 0) * 4.0, delay_s=1.0)
