#!/usr/bin/env python3

# Filename: A11_m_server_rawtubes.py

from pygame.color import THECOLORS

from A09_vec2d import Vec2D

from A10_m_server_baseline import make_some_pucks as base_make_some_pucks
from A10_m_game_loop import GameLoop
import A10_m_globals as g

from A11_m_air_table_objects import Puck, Tube
version = "11"

def demo7_setup():
    puck1 = Puck(Vec2D(1.5, 7.5), 0.4, 0.3)

    tube1 = Tube(g.game_window.center_2d_m - Vec2D(1.5, 0.0), "local")
    g.air_table.raw_tubes.append(tube1)
    
    tube2 = Tube(g.game_window.center_2d_m, "local")
    g.air_table.raw_tubes.append(tube2)
    
    tube3 = Tube(g.game_window.center_2d_m + Vec2D(1.5, 0.0), "local")
    g.air_table.raw_tubes.append(tube3)

def make_some_pucks(demo):
    base_make_some_pucks(demo, version=version, customDemo7=demo7_setup)

#============================================================
# main procedural script
#============================================================

def main():
    game_loop = GameLoop(engine_type="circular", window_width_px=900, 
                         make_some_pucks=make_some_pucks, version=version)
    game_loop.start(demo_index=7)

#============================================================
# Start everything.
#============================================================
        
if __name__ == '__main__':
    main()