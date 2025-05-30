#!/usr/bin/env python3

# Filename: A16c_2D_B2D_serverN.py

import math

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Wall, Puck, Spring
from A15_game_loop import GameLoop
from A15_pool_shots import pool_trick_shot, pool_line_of_balls, burst_of_pucks
import A15_globals as g

#===========================================================
# Functions
#===========================================================

def make_some_pucks(demo):
    g.game_window.set_caption("PyBox2D Air-Table Server A16c     Demo #" + str(demo))
    g.env.timestep_fixed = False

    # This removes all references to pucks and walls and effectively deletes them. 
    for eachpuck in g.air_table.pucks[:]:
        eachpuck.delete()
        
    for eachWall in g.air_table.walls[:]:
        if not eachWall.fence:
            eachWall.delete()

    g.air_table.resetFence()
    g.air_table.buildFence() # a complete perimeter fence

    # Most of the demos don't need the tangle checker.
    g.air_table.jello_tangle_checking_enabled = False
    
    # Make sure the throwing thread is not still running.
    g.air_table.delayed_throw = None

    # Now just black out the screen.
    g.game_window.clear()

    g.env.fr_avg.reset()
    g.env.tickCount = 0

    for client_name in g.env.clients:
        client = g.env.clients[client_name]
        if client.drone:
            client.active = False
            client.drone = False

    # Each demo will have a single variation unless specified.
    g.env.demo_variations[demo]['count'] = 1

    if demo == 1:
        g.env.set_gravity("off")
        #    position       , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, color=THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3)
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3) 
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
        g.env.set_gravity("off")
        initial_states = [
            {"p1": {"rps":  4.0, "color": THECOLORS["brown"]},
             "p2": {"rps":  2.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  2.0, "color": THECOLORS["tan"]},
             "p2": {"rps": -2.0, "color": THECOLORS["brown"]}},

            {"p1": {"rps":  3.1, "color": THECOLORS["tan"]},
             "p2": {"rps":  3.1, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  0.0, "color": THECOLORS["white"]},
             "p2": {"rps":  2.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  3.0, "color": THECOLORS["white"]},
             "p2": {"rps":  6.0, "color": THECOLORS["tan"]}},

            {"p1": {"rps": -3.1, "color": THECOLORS["tan"]},
             "p2": {"rps": -3.1, "color": THECOLORS["tan"]}},

            {"p1": {"rps":  0.0, "color": THECOLORS["tan"]},
             "p2": {"rps":  0.0, "color": THECOLORS["tan"]}}
        ]
        g.env.demo_variations[2]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[2]['index']]
        print("Variation", g.env.demo_variations[2]['index'] + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"])

        p1 = Puck( Vec2D(2.0, 2.0), 1.7, 1.0, 
            border_px=10, color=state["p1"]["color"],
            angularVelocity_rps=state["p1"]["rps"],
            coef_rest=0.0, CR_fixed=True, 
            friction=2.0, friction_fixed=True
        )
        p2 = Puck( Vec2D(8.0, 6.75), 1.7, 1.0, 
            border_px=10, color=state["p2"]["color"],
            angularVelocity_rps=state["p2"]["rps"],
            coef_rest=0.0, CR_fixed=True,
            friction=2.0, friction_fixed=True
        )

        spring_strength_Npm2 = 20.0
        spring_length_m = 1.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.15, c_damp=50.0, color=THECOLORS["yellow"])
    
        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[2]['index'] + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f})"
        )

    elif demo == 3:
        g.air_table.buildFence(onoff={'L':True,'R':True,'T':False,'B':True})
        g.env.set_gravity("off")
        initial_states = [
            {"p1": {"rps":   4.0, "color": THECOLORS["white"]},
             "p2": {"rps": -34.0, "color": THECOLORS["darkred"]},
             "p3": {"rps":  30.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":   0.0, "color": THECOLORS["white"]},
             "p2": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p3": {"rps": -15.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":  11.0, "color": THECOLORS["white"]},
             "p2": {"rps":   0.0, "color": THECOLORS["blue"]},
             "p3": {"rps":   0.0, "color": THECOLORS["blue"]}},

            {"p1": {"rps":  30.0, "color": THECOLORS["white"]},
             "p2": {"rps":   0.0, "color": THECOLORS["blue"]},
             "p3": {"rps": -30.0, "color": THECOLORS["white"]}},

            {"p1": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p2": {"rps":   4.0, "color": THECOLORS["darkred"]},
             "p3": {"rps":   4.0, "color": THECOLORS["darkred"]}}
        ]
        g.env.demo_variations[3]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[3]['index']]
        print("Variation", g.env.demo_variations[3]['index'] + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"],
              "   p3_rps =", state["p3"]["rps"])
        
        p1p3_y_m = 2.3
        p1 = Puck( Vec2D(2.0, p1p3_y_m), 1.2, 1.0, 
            angularVelocity_rps=state["p1"]["rps"],
            coef_rest=0.0, CR_fixed=True, 
            friction=2.0, friction_fixed=True,
            border_px=10, color=state["p1"]["color"]
        )
        p3 = Puck( Vec2D(8.0, p1p3_y_m), 1.2, 1.0, 
            angularVelocity_rps=state["p3"]["rps"],
            coef_rest=0.0, CR_fixed=True, 
            friction=2.0, friction_fixed=True,
            border_px=10, color=state["p3"]["color"]
        )
        # Equilateral triangle:  h = (1/2) * √3 * a
        y_m = p1.pos_2d_m.y + (p3.pos_2d_m.x - p1.pos_2d_m.x) * 3**0.5 / 2.0
        x_m = p1.pos_2d_m.x + (p3.pos_2d_m.x - p1.pos_2d_m.x)/2.0
        p2 = Puck( Vec2D(x_m, y_m), 1.2, 1.0, 
            angularVelocity_rps=state["p2"]["rps"],
            coef_rest=0.0, CR_fixed=True, 
            friction=2.0, friction_fixed=True,
            border_px=10, color=state["p2"]["color"]
        )

        spring_strength_Npm2 = 15.0
        spring_length_m = 1.0
        spring_width_m = 0.10
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p1, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[3]['index'] + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f}, {state['p3']['rps']:.1f})"
        )

    elif demo == 4:
        g.env.set_gravity("on")
        initial_states = [
            {'w1':{'angle_d':-0.17},'w2':{'angle_d':+4.00}},
            {'w1':{'angle_d':-5.00},'w2':{'angle_d':+2.00}},
            {'w1':{'angle_d':-9.00},'w2':{'angle_d':+1.00}},
            {'w1':{'angle_d': 0.00},'w2':{'angle_d':+9.00}},
            {'funnel_angle_d': 5},
            {'funnel_angle_d':15},
            {'funnel_angle_d':25},
            {'funnel_angle_d':35},
            {'funnel_angle_d':45}
        ]
        g.env.demo_variations[4]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[4]['index']]

        # For the first group of variations, add a grid of pucks.
        if 'w1' in state:
            spacing_factor = 1.0
            grid_size = 10,5
            for j in range(grid_size[0]):
                for k in range(grid_size[1]):
                    if (k >= 1 and k <= 3):
                        puck_color_value = THECOLORS['orange']
                    else:
                        puck_color_value = THECOLORS['grey']

                    offset_2d_m = Vec2D(0.0, 4.5)
                    spacing_factor = 0.7
                    position_2d_m = Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)) + offset_2d_m

                    Puck(position_2d_m, radius_m=0.25, density_kgpm2=1.0,
                            color=puck_color_value,
                            CR_fixed=True, coef_rest=0.8, friction=0.05, friction_fixed=True)

            Wall(Vec2D(4.0, 4.5), half_width_m=4.0, half_height_m=0.04, border_px=0,
                angle_radians=state['w1']['angle_d']*(math.pi/180)
            )
            Wall(Vec2D(7.0, 2.5), half_width_m=3.0, half_height_m=0.04, border_px=0,
                angle_radians=state['w2']['angle_d']*(math.pi/180)
            )
            details_desc = f"w1 angle = {state['w1']['angle_d']}   w2 angle = {state['w2']['angle_d']}"
        
        # Two walls symmetrically angled to produce a funnel at the bottom of the window, two pucks.
        elif 'funnel_angle_d' in state:
            # No side walls:
            g.air_table.buildFence(onoff={'L':False,'R':False,'T':True,'B':True})
            
            c_f = 1.0
            y_m = 7.0
            x_m = 0.0
            Puck(Vec2D(x_m,y_m), radius_m=1.25, density_kgpm2=1.0, CR_fixed=True, coef_rest=0.7, friction=c_f, friction_fixed=True)
            x_m = g.air_table.walls_dic['R_m']
            Puck(Vec2D(x_m,y_m), radius_m=1.25, density_kgpm2=1.0, CR_fixed=True, coef_rest=0.7, friction=c_f, friction_fixed=True)

            angle_d = state['funnel_angle_d']
            hw_m = 100.0
            hh_m = 0.10
            y_m = math.sin(angle_d * (math.pi/180)) * hw_m # Position walls so their center end is at the bottom of the window.
            cf_touch = math.cos(angle_d * (math.pi/180))   # Position walls so their center ends touch.
            x_m = (0.5 * g.air_table.walls_dic['R_m']) - cf_touch * hw_m
            Wall(Vec2D( x_m, y_m), half_width_m=hw_m, half_height_m=hh_m, border_px=0, angle_radians=-angle_d*(math.pi/180))
            x_m = (0.5 * g.air_table.walls_dic['R_m']) + cf_touch * hw_m
            Wall(Vec2D( x_m, y_m), half_width_m=hw_m, half_height_m=hh_m, border_px=0, angle_radians=+angle_d*(math.pi/180))

            details_desc = f"funnel angle = {state['funnel_angle_d']}"

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[4]['index'] + 1}" +
            f"     {details_desc}"
        )

    elif demo == 5:
        g.env.set_gravity("off")
        """
        Spring-pinned pucks are placed in a regular-polygons arrangement. Pucks are placed
        at at polygon radius, R = r_puck / sin(π/n). The spring pins are positioned closer
        to the center providing tension to hold the pucks in contact.
        """
        initial_states = [
            {'n_pucks':2},
            {'n_pucks':3},
            {'n_pucks':4},
            {'n_pucks':5},
            {'n_pucks':6},
            {'n_pucks':7},
            {'n_pucks':8},
            {'n_pucks':9},
            {'n_pucks':1}
        ]
        g.env.demo_variations[5]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[5]['index']]
        
        # no fence:
        g.air_table.buildFence(onoff={'L':False,'R':False,'T':False,'B':False})

        n_pucks = state['n_pucks']

        if n_pucks == 1:
            g.air_table.pinnedPuck(g.game_window.center_2d_m, radius_m=1.8)
        else:
            radius_m = 1.5
            polygon_radius_m = radius_m / math.sin(math.pi/n_pucks)
            center_to_puck_2d_m = Vec2D(0.0, polygon_radius_m)
            pin_offset_m = 0.4
            center_to_pin_2d_m = Vec2D(0.0, polygon_radius_m - pin_offset_m)
            for i in range(0, n_pucks):
                angle = (360 / n_pucks) * i

                rotated_c_to_puck_2d_m = center_to_puck_2d_m.rotated(angle)
                puck_position_2d_m = g.game_window.center_2d_m + rotated_c_to_puck_2d_m

                rotated_c_to_pin_2d_m = center_to_pin_2d_m.rotated(angle)
                pin_position_2d_m = g.game_window.center_2d_m + rotated_c_to_pin_2d_m

                g.air_table.pinnedPuck(puck_position_2d_m, radius_m=radius_m, 
                                       pin_position_2d_m=pin_position_2d_m)

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[5]['index'] + 1}" +
            f"     pinned pucks = {n_pucks}"
        )

    elif demo == 6:
        g.env.set_gravity("off")
        initial_states = [
            {'type':'three-pucks'},
            {'type':'two-pucks'}
        ]
        g.env.demo_variations[6]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[6]['index']]
        
        if state['type'] == 'three-pucks':
            density = 1.5
            radius = 0.7
            coef_rest_puck = 0.3

            p1 = Puck(Vec2D(2.00, 3.00), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
            p2 = Puck(Vec2D(3.50, 4.50), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
            p3 = Puck(Vec2D(5.00, 3.00), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
            
            # No springs on this one.
            Puck(Vec2D(3.50, 7.00), 0.95, density, coef_rest=coef_rest_puck, CR_fixed=True)

            spring_strength_Npm2 = 400.0
            spring_length_m = 2.5
            spring_width_m = 0.07
            spring_drag = 0.0
            spring_damper = 5.0

            Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
                c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["red"])
            Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
                c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["tan"])
            Spring(p3, p1, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
                c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["gold"])

        elif state['type'] == 'two-pucks':
            p1 = Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
            p2 = Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
            
            spring_strength_Npm2 = 20.0 #18.0
            spring_length_m = 1.5
            Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.2)

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[6]['index'] + 1}"
        )

    elif demo == 7:
        def two_drone_special__rectangular():
            density = 0.7

            # a large pinned circular puck with a visible spoke
            #                              , r_m , density
            tempPuck = Puck(Vec2D(4.0, 1.0), 0.55, density, 
                angularVelocity_rps=0.5, color=THECOLORS["orange"], show_health=True, hit_limit=10
            )
            Spring(tempPuck, Vec2D(4.0, 1.0), strength_Npm=300.0, 
                pin_radius_m=0.03, width_m=0.02, c_drag = 1.5)
            
            # two pinned rectangles
            puck_position = Vec2D(0.0, g.game_window.UR_2d_m.y) + Vec2D(2.0, -2.0) # starting from upper left
            tempPuck = Puck(puck_position, 1.4, density, 
                angularVelocity_rps=0.5, rect_fixture=True, hw_ratio=0.1, show_health=True
            )
            Spring(tempPuck, puck_position, strength_Npm=300.0, 
                pin_radius_m=0.03, width_m=0.02, c_drag=10.0)
            
            puck_position = Vec2D(8.5, 4.0)
            tempPuck = Puck(puck_position, 1.4, density, 
                angularVelocity_rps=0.5, rect_fixture=True, hw_ratio=0.1, show_health=True
            )
            Spring(tempPuck, puck_position, strength_Npm=300.0, 
                pin_radius_m=0.03, width_m=0.02, c_drag=10.0)

            # row of small pinned pucks without spokes
            for m in range(0, 6):
                pinPoint_2d_m = Vec2D(2.0 + (m * 0.65), 4.0)
                tempPuck = Puck(pinPoint_2d_m, 0.25, density, color=THECOLORS["orange"], 
                                show_health=True, hit_limit=15, showSpoke=False)
                Spring(tempPuck, pinPoint_2d_m, strength_Npm=300.0, 
                    width_m=0.02, c_drag=1.5, pin_radius_m=0.03)
            
            # Make user/client controllable pucks for all the clients.
            y_puck_position_m = 1.0
            for client_name in g.env.clients:
                client = g.env.clients[client_name]
                if client.active and not client.drone:
                    # Box2D drag modeling is slightly different than that in the circular
                    # engines. So, c_drag set higher than the default value, 0.7.
                    g.air_table.buildControlledPuck( x_m=6.4, y_m=y_puck_position_m, r_m=0.45, client_name=client_name, sf_abs=False, c_drag=1.5)
                    y_puck_position_m += 1.2
                            
            # drone pucks
            g.air_table.buildControlledPuck( x_m=1.0, y_m=1.0, r_m=0.55, client_name="C5", sf_abs=False, drone=True, bullet_age_limit_s=3.0)
            g.air_table.buildControlledPuck( x_m=8.5, y_m=7.0, r_m=0.55, client_name="C6", sf_abs=False, drone=True, bullet_age_limit_s=3.0)
        
        def rectangle_in_middle():
            g.air_table.buildFence(onoff={'L':True,'R':False,'T':True,'B':True})

            density = 0.7
            puck_position_2d_m = g.game_window.center_2d_m
            tempPuck = Puck(puck_position_2d_m, 3.0, density, 
                angularVelocity_rps=0.5, rect_fixture=True, hw_ratio=0.05, show_health=True
            )
            Spring(tempPuck, puck_position_2d_m, strength_Npm=300.0, 
                pin_radius_m=0.03, width_m=0.02, c_drag=10.0)
            
            radius_m = 0.45
            set_off_m = radius_m + 0.5
            init_2d_m = Vec2D(set_off_m, set_off_m)
            g.air_table.buildControlledPuck(x_m=init_2d_m.x, y_m=init_2d_m.y, r_m=radius_m, client_name='local', sf_abs=False, c_drag=1.5)

        g.air_table.puckPopper_variations(demo, two_drone_special__rectangular, custom_1=rectangle_in_middle)
        
    elif demo == 8:
        g.env.set_gravity("on")
        g.air_table.throwJello_variations(demo)

    elif demo == 9:
        g.env.set_gravity("off")
        g.air_table.targetJello_variations(demo)
    
    elif demo == 0:
        # Demo 0 has four variations showing different puck arrangements and collisions:
        # a: Dominoes - Creates a row of increasingly larger rectangular pucks,
        #    then throws a small round puck to start a chain reaction
        # b: Pyramid stack - Builds a pyramid of tall rectangular pucks on the ground,
        #    then launches a heavy bowling ball at it
        # c: Billiards trick shot - Arranges circular pucks in a partial ring formation,
        #    with a cue ball that's shot to scatter them
        # d: Line of balls - Creates a line of identical circular pucks and a cue ball 
        #    with adjustable vertical offset (0%, 10%, or 50%) to demonstrate different 
        #    collision patterns

        initial_states = [
            {'variation':'a'},
            {'variation':'b'},
            {'variation':'c'},
            
            {'variation':'d', 'offset_percent':0},
            {'variation':'d', 'offset_percent':10},
            {'variation':'d', 'offset_percent':50},

            {'variation':'e', 'n_pucks':8},
            {'variation':'e', 'n_pucks':32},
            {'variation':'e', 'n_pucks':64},
            {'variation':'e', 'n_pucks':128},

            {'variation':'f'}
        ]
        g.env.demo_variations[demo]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[demo]['index']]
        
        extra_note = ""

        if state['variation'] == 'a':
            g.air_table.buildFence(onoff={'L':True,'R':True,'T':False,'B':True})
            g.env.set_gravity("on")
            density = 0.7
            half_width_m = 0.01
            hw_ratio = 9.0
            x_position_m = 0.3
            for j in range(0, 9):
                y_puck_position_m = (half_width_m * hw_ratio) + 0.01
                Puck(Vec2D(x_position_m, y_puck_position_m), half_width_m, density, 
                    coef_rest=0.82,
                    color=THECOLORS['darkkhaki'], border_px=0,
                    rect_fixture=True, hw_ratio=hw_ratio, angle_r=0)
                half_width_m *= 1.5
                x_position_m *= 1.5

            # Throw a puck to get the chain reaction started.
            p1 = Puck(Vec2D(0.15, 0.06), 0.06, density, rect_fixture=False, angularVelocity_rps=0, 
                      bullet=True, color=THECOLORS['royalblue'], border_px=0)

            g.air_table.throw_puck(p1, Vec2D(1, 2) * 0.5, delay_s=2.0)

        elif state['variation'] == 'b':
            g.air_table.buildFence(onoff={'L':True,'R':True,'T':False,'B':True})
            g.env.set_gravity("on")

            # Pyramid on the ground
            puck_half_width_m = 0.1
            hw_ratio = 3.0 # height/width
            puck_half_height_m = puck_half_width_m * hw_ratio
            density = 1.0
            n_rows = 11

            x_gap_fraction = 0.70
            deltaX_m = 2*puck_half_width_m + (2*puck_half_width_m * x_gap_fraction)
            y_gap_fraction = 0.03
            deltaY_m = 2*puck_half_height_m + (2*puck_half_height_m * y_gap_fraction)

            x_position_start_m = 1.0
            x_position_m = x_position_start_m
            y_position_m = puck_half_height_m + (2*puck_half_height_m * y_gap_fraction)

            for i in range(n_rows):
                for j in range(i, n_rows):
                    Puck(Vec2D(x_position_m, y_position_m), puck_half_width_m, density, 
                        color=THECOLORS['darkkhaki'], border_px=0,
                        rect_fixture=True, hw_ratio=hw_ratio, angle_r=0, awake=False,
                        coef_rest=0.8, CR_fixed=True)
                    x_position_m += deltaX_m
                y_position_m += deltaY_m
                x_position_m = x_position_start_m + ((i+1) * deltaX_m/2.0)

            # This puck will be flung or bowled by the user at the target stack
            bowlingBall_density = 3.0
            bowlingBall_r_m = 0.3
            p1 = Puck(Vec2D(9.0, bowlingBall_r_m), bowlingBall_r_m, bowlingBall_density,
                        coef_rest=0.7, CR_fixed=True,
                        bullet=True, angularVelocity_rps=0, color=THECOLORS['royalblue'], border_px=0)
            
            g.air_table.throw_puck(p1, Vec2D(-10, 1.0) * 10, delay_s=2.0)

        elif state['variation'] == 'c':
            g.env.set_gravity("off")
            pool_trick_shot()

        elif state['variation'] == 'd':
            g.air_table.buildFence(onoff={'L':False,'R':False,'T':False,'B':False})
            g.env.set_gravity("off")
            pool_line_of_balls(state['offset_percent'])
            extra_note = f"offset_percent = {state['offset_percent']}"

        elif state['variation'] == 'e':
            g.env.set_gravity("off")
            g.air_table.makeSquareFence()
            g.air_table.buildFence(onoff={'L':True,'R':True,'T':True,'B':True})

            burst_of_pucks(state['n_pucks'], speed_mps=3, radius_m=0.1)
            extra_note = f"n_pucks = {state['n_pucks']}"

        elif state['variation'] == 'f':
            g.env.set_gravity("off")
            g.air_table.makeSquareFence()
            g.air_table.buildFence(onoff={'L':True,'R':True,'T':True,'B':True})

            radius_m = 0.4

            x_m = g.game_window.center_2d_m.x
            y_m = g.game_window.UR_2d_m.y - radius_m
            cue_pos_2d_m = Vec2D(x_m, y_m)

            # Now adjust the cue ball position so that it is not touching the wall.
            cue_pos_2d_m -= Vec2D(0.1, 0.1)

            p1 = Puck(cue_pos_2d_m, radius_m, 0.3, coef_rest=1.0, friction=0.0, color=THECOLORS["orange"], showSpoke=False)
            g.air_table.throw_puck(p1, Vec2D(-1, -1) * 2.0, delay_s=1.0)

            # Group of target pucks
            target_pos_2d_m = cue_pos_2d_m - Vec2D(2.00, 2.00)

            for i in range(2):
                Puck(target_pos_2d_m, radius_m, 0.3, coef_rest=1.0, friction=0.0, showSpoke=False)
                target_pos_2d_m -= Vec2D(1.00, 1.00)

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[demo]['index'] + 1}    {extra_note}"
        )
            
    else:
        print("Nothing set up for this key.")

#============================================================
# main procedural script
#============================================================

def main():
    game_loop = GameLoop(engine_type="box2d", window_width_px=900, make_some_pucks=make_some_pucks)
    g.game_loop = game_loop
    game_loop.start(demo_index=7)

#============================================================
# Start everything.
#============================================================

if __name__ == '__main__':
    main()
