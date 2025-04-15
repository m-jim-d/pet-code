#!/usr/bin/env python3

# Filename: A15c_2D_perfect_kiss_serverN.py

import random

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Puck
from A15_game_loop import GameLoop
from A15a_2D_finished_game import make_some_pucks as A15a_make_some_pucks
import A15_globals as g

#===========================================================
# Functions
#===========================================================

def setup_pool_shot():
    g.env.timestep_fixed = True
    g.env.constant_dt_s = 1/20.0
    
    g.air_table.inhibit_wall_collisions = True
    g.env.inhibit_screen_clears = True
    
    # Randomize the starting x position of the incoming puck. 
    # Elastic pucks make it reversible.
    Puck(Vec2D(random.random()-0.3, 4.80), 0.45, 0.3, color=THECOLORS["orange"], coef_rest=1.0, CR_fixed=True, 
               vel_2d_mps=Vec2D(  25.0, 0.0))
    # Target puck:
    Puck(Vec2D(4.0,                 4.30), 0.45, 0.3,                            coef_rest=1.0, CR_fixed=True, 
               vel_2d_mps=Vec2D(   0.0, 0.0))
    
def make_some_pucks(demo):
    g.game_window.set_caption("Perfect Kiss Air-Table Server A15c     Demo #" + str(demo))
    
    g.air_table.correct_for_wall_penetration = True
    g.air_table.correct_for_puck_penetration = True
    g.air_table.collision_count = 0
    g.air_table.count_direction = 1
    g.air_table.timeDirection = 1
    g.air_table.perfect_kiss = False

    def demos_for_perfectKiss(demo):
        if demo == '1p':
            # Basic pool shot, no penetration correction, no perfect kiss
            g.air_table.correct_for_puck_penetration = False
            g.air_table.perfect_kiss = False
            setup_pool_shot()
            return True
            
        elif demo == '2p':
            # Pool shot with penetration correction only
            g.air_table.correct_for_puck_penetration = True
            g.air_table.perfect_kiss = False
            setup_pool_shot()
            return True
            
        elif demo == '3p':
            # Pool shot with both penetration correction and perfect kiss
            g.air_table.correct_for_puck_penetration = True
            g.air_table.perfect_kiss = True
            setup_pool_shot()
            return True
        
        else:
            return False

    A15a_make_some_pucks(demo, specials=demos_for_perfectKiss)

#============================================================
# main procedural script
#============================================================

def main():
    game_loop = GameLoop(engine_type="circular-perfectKiss", window_width_px=900, make_some_pucks=make_some_pucks)
    game_loop.start(demo_index=7)

#============================================================
# Start everything.
#============================================================
        
if __name__ == '__main__':
    main()
