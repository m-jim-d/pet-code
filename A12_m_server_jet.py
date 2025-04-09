#!/usr/bin/env python3

# Filename: A12_m_server_jet.py

from pygame.color import THECOLORS

from A09_vec2d import Vec2D

from A10_m_server_baseline import make_some_pucks as base_make_some_pucks
from A10_m_game_loop import GameLoop
import A10_m_globals as g

from A12_m_air_table_objects import Puck, Tube, Jet
version = "12"

def demo7_setup():
    puck1 = Puck(Vec2D(4.0, 5.5), 0.4, 0.3, client_name="local")
    puck1.jet = Jet(puck1)
    puck1.tube = Tube(puck1)
    g.air_table.raw_tubes.append(puck1.tube)

    puck2 = Puck(Vec2D(6.5, 5.5), 0.4, 0.3, client_name="C1")
    puck2.jet = Jet(puck2)
    puck2.tube = Tube(puck2)
    g.air_table.raw_tubes.append(puck2.tube)

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