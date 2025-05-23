#!/usr/bin/env python3

# Filename: A15a_2D_finished_game.py

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Puck, Spring
from A15_game_loop import GameLoop
from A15_pool_shots import pool_trick_shot, pool_line_of_balls, burst_of_pucks
import A15_globals as g

#===========================================================
# Functions
#===========================================================

def two_drone_special__circular():
    g.air_table.coef_rest = 1.00
    
    # Make user/client controllable pucks for all the active clients.
    y_position_m = 1.0
                
    # Arrange human-controlled pucks in a column.
    for name in g.env.clients:
        client = g.env.clients[name]
        if client.active and (not client.drone):
            g.air_table.buildControlledPuck(x_m=7.0, y_m=y_position_m, r_m=0.45, client_name=name, 
                                            sf_abs=False, c_drag=0.7)
            y_position_m += 1.3
    
    # Position the drone-controlled pucks in specific locations.      
    g.air_table.buildControlledPuck( x_m=3.0, y_m=7.0, r_m=0.55, client_name="C5", sf_abs=False, drone=True)  
    g.air_table.buildControlledPuck( x_m=3.0, y_m=1.0, r_m=0.55, client_name="C6", sf_abs=False, drone=True)
    
    # Make some pucks that are not controllable.
    density = 0.7
    
    # Make a horizontal row of pinned-spring pucks.
    for m in range(0, 6): 
        pinPoint_2d = Vec2D(2.0 + (m * 0.65), 4.5)
        tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
        Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, 
            pin_radius_m=0.03, width_m=0.02, c_drag=1.5)
    
    # Make a vertical column of pinned-spring pucks.
    for m in range(-3, 4):
        pinPoint_2d = Vec2D(2 + 6*0.65, 4.5 + m*0.65)
        tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
        Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, 
            pin_radius_m=0.03, width_m=0.02, c_drag=1.5)
    
    # One free standing puck
    Puck( Vec2D(9.0, 4.5), 0.7, density, color=THECOLORS["cyan"], hit_limit=20, c_drag=0.7, show_health=True)

def no_drone_custom1__circular():
    density = 0.7
    puck_position_2d_m = g.game_window.center_2d_m
    tempPuck = Puck(puck_position_2d_m, 1.0, density, 
        angularVelocity_rps=0.5, rect_fixture=False, show_health=True
    )
    Spring(tempPuck, puck_position_2d_m, strength_Npm=300.0, 
        pin_radius_m=0.03, width_m=0.02, c_drag=10.0)

    radius_m = 0.45
    set_off_m = radius_m + 0.5
    init_2d_m = Vec2D(set_off_m, set_off_m)
    g.air_table.buildControlledPuck(x_m=init_2d_m.x, y_m=init_2d_m.y, r_m=radius_m, client_name='local', sf_abs=False, c_drag=1.5)
    
def make_some_pucks(demo, specials=None, caption="A15a"):
    g.game_window.set_caption(f"Air-Table Server {caption} {g.air_table.engine}    Demo #" + str(demo))
    g.env.timestep_fixed = False

    # This removes all references to pucks and effectively deletes them.
    for eachpuck in g.air_table.pucks[:]:
        eachpuck.delete()

    g.air_table.resetFence()

    # Most of the demos don't need the tangle checker.
    g.air_table.jello_tangle_checking_enabled = False
    
    # Make sure the throwing thread is not still running.
    g.air_table.delayed_throw = None
    
    # Now just black out the screen.
    g.game_window.clear()

    g.env.fr_avg.reset()
    g.env.tickCount = 0
    g.air_table.coef_rest = 1.00
    g.air_table.time_s = 0.0
    
    g.env.inhibit_screen_clears = False
    g.air_table.inhibit_wall_collisions = False
    g.air_table.inhibit_all_puck_collisions = False

    # Each demo will have a single variation unless specified.
    g.env.demo_variations[demo]['count'] = 1

    g.env.set_gravity("off")
    
    demo_in_specials = False

    if demo == 1:
        #    position       , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, color=THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3)
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3)
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
        spacing_factor = 2.0
        grid_size = 4,2
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k)==(1,1)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]
                
                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.75, 0.3, color=puck_color_value)
    
    elif demo == 3:
        spacing_factor = 1.5
        grid_size = 5,3
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k)==(2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]

                Puck(Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)), 0.55, 0.3, color=puck_color_value)
    
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
        p1 = Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        p2 = Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
        density = 0.9
        radius = 0.75
        coef_rest_puck = 0.7

        p1 = Puck(Vec2D(2.00, 3.00), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        p2 = Puck(Vec2D(3.50, 4.50), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        p3 = Puck(Vec2D(5.00, 3.00), radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        
        # No springs on this one.
        Puck(Vec2D(3.50, 7.00), 0.90, density, coef_rest=coef_rest_puck, CR_fixed=True)

        spring_strength_Npm2 = 250 # 250
        spring_length_m = 2.5
        spring_width_m = 0.07
        spring_drag = 0.5 # default is 0.0
        spring_damper = 5.0

        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["red"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["tan"])
        Spring(p3, p1, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["gold"])

    elif demo == 7:
        g.air_table.puckPopper_variations(demo, two_drone_special__circular, custom_1=no_drone_custom1__circular)
        
    elif demo == 8:
        g.env.set_gravity("on")
        g.air_table.throwJello_variations(demo)

    elif demo == 9:
        g.air_table.targetJello_variations(demo)
    
    elif demo == 0:
        initial_states = [
            {'variation':'a'},

            {'variation':'b', 'offset_percent':0},
            {'variation':'b', 'offset_percent':10},
            {'variation':'b', 'offset_percent':50},

            {'variation':'c', 'n_pucks':4},
            {'variation':'c', 'n_pucks':8},
            {'variation':'c', 'n_pucks':16},
            {'variation':'c', 'n_pucks':32},
            {'variation':'c', 'n_pucks':64},
            {'variation':'c', 'n_pucks':128},
            {'variation':'c', 'n_pucks':500},
            {'variation':'c', 'n_pucks':1000},
            {'variation':'c', 'n_pucks':2000},

            {'variation':'d'}
        ]
        g.env.demo_variations[demo]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[demo]['index']]
        
        extra_note = ""
        
        if state['variation'] == 'a':
            g.air_table.inhibit_wall_collisions = True
            g.env.set_gravity("off")
            pool_trick_shot()

            extra_note = "polygon setup"

        elif state['variation'] == 'b':
            g.air_table.inhibit_wall_collisions = True
            g.env.set_gravity("off")
            pool_line_of_balls(state['offset_percent'])

            extra_note = f"offset % = {state['offset_percent']}"
        
        elif state['variation'] == 'c':
            g.env.set_gravity("off")
            g.air_table.makeSquareFence()

            burst_of_pucks(state['n_pucks'])
            extra_note = f"n_pucks = {state['n_pucks']}"

        elif state['variation'] == 'd':
            g.air_table.makeSquareFence()

            radius_m = 0.4

            x_m = g.game_window.center_2d_m.x
            y_m = g.game_window.UR_2d_m.y - radius_m
            cue_pos_2d_m = Vec2D(x_m, y_m)

            # Now adjust the cue ball position so that it is not touching the wall.
            cue_pos_2d_m -= Vec2D(0.1, 0.1)

            p1 = Puck(cue_pos_2d_m, radius_m, 0.3, coef_rest=1.0, color=THECOLORS["orange"])
            g.air_table.throw_puck(p1, Vec2D(-1, -1) * 2.0, delay_s=1.0)

            # Group of target pucks
            target_pos_2d_m = cue_pos_2d_m - Vec2D(2.00, 2.00)

            for i in range(2):
                Puck(target_pos_2d_m, radius_m, 0.3, coef_rest=1.0)
                target_pos_2d_m -= Vec2D(1.00, 1.00)

        g.game_window.set_caption( g.game_window.caption + 
            f"     Variation {g.env.demo_variations[demo]['index'] + 1}    {extra_note}"
        )

    elif specials:
        demo_in_specials = specials(demo)

    else:
        if not demo_in_specials: 
            print("Nothing set up for this key.")

#============================================================
# main procedural script
#============================================================

def main():
    game_loop = GameLoop(engine_type="circular", window_width_px=900, make_some_pucks=make_some_pucks)
    g.game_loop = game_loop
    game_loop.start(demo_index=7)

#============================================================
# Start everything.
#============================================================
        
if __name__ == '__main__':
    main()
