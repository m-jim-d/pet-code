#!/usr/bin/env python3

# Filename: A10_m_server_baseline.py

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A10_m_air_table_objects import Puck, Spring
from A10_m_game_loop import GameLoop
import A10_m_globals as g
from A15_pool_shots import pool_line_of_balls, pool_trick_shot

#===========================================================
# Functions
#===========================================================

def make_some_pucks(demo, customDemo7=None, version="10"):
    g.game_window.set_caption(f"Air-Table Server A{version}     Demo #{demo}")
    g.env.timestep_fixed = False

    # This removes all references to pucks and walls and effectively deletes them. 
    for eachpuck in g.air_table.pucks[:]:
        eachpuck.delete()

    for eachTube in g.air_table.raw_tubes[:]:
        eachTube.delete()
    
    # Make sure the throwing thread is not still running.
    g.air_table.delayed_throw = None
        
    # Now just black out the screen.
    g.game_window.clear()

    g.env.fr_avg.reset()
    g.env.tickCount = 0
    g.air_table.coef_rest = 1.00
    g.air_table.time_s = 0.0

    g.air_table.inhibit_wall_collisions = False

    # Each demo will have a single variation unless specified.
    g.env.demo_variations[demo]['count'] = 1

    g.env.set_gravity("off")

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
        if customDemo7: 
            customDemo7()
        else:
            Puck(Vec2D(2.00, 3.00),  0.4, 0.3, coef_rest=1.0)
            p1 = Puck(Vec2D(6.00, 7.00),  0.4, 0.3, coef_rest=1.0, color=THECOLORS["orange"])
            g.air_table.throw_puck(p1, Vec2D(-1, -1) * 5.0, delay_s=1.0)

    elif demo == 8:
        initial_states = [
            {'offset_percent':  0},
            {'offset_percent': 10},
            {'offset_percent': 20},
            {'offset_percent': 40},
            {'offset_percent': 50}
        ]
        g.env.demo_variations[demo]['count'] = len(initial_states)
        state = initial_states[g.env.demo_variations[demo]['index']]

        pool_line_of_balls(state['offset_percent'])

    elif demo == 9:
        pool_trick_shot()

    else:
        print("Nothing set up for this key.")

#============================================================
# main procedural script
#============================================================

def main():
    game_loop = GameLoop(engine_type="circular", window_width_px=900, 
                         make_some_pucks=make_some_pucks, version="10")
    game_loop.start(demo_index=7)

#============================================================
# Start everything.
#============================================================
        
if __name__ == '__main__':
    main()
