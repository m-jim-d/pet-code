#!/usr/bin/env python3

# Filename: A16c_2D_B2D_serverN.py

import math

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Wall, Puck, Spring
from A15_game_loop import GameLoop

import A15_globals as g

#===========================================================
# Functions
#===========================================================
        
def make_some_pucks(demo):
    g.game_window.update_caption("PyBox2D Air-Table Server A16c     Demo #" + str(demo))
    g.env.timestep_fixed = False

    # This removes all references to pucks and walls and effectively deletes them. 
    for eachpuck in g.air_table.pucks[:]:
        eachpuck.delete()
    if g.air_table.engine == "box2d":
        for eachWall in g.air_table.walls[:]:
            if not eachWall.fence:
                eachWall.delete()

    # Most of the demos don't need the tangle checker.
    g.air_table.jello_tangle_checking_enabled = False
    
    # Now just black out the screen.
    g.game_window.clear()

    g.env.fr_avg.reset()
    g.env.tickCount = 0

    for client_name in g.env.clients:
        client = g.env.clients[client_name]
        if client.drone:
            client.active = False
            client.drone = False

    if demo == 1:
        #    position       , r_m , density
        Puck(Vec2D(2.5, 7.5), 0.25, 0.3, color=THECOLORS["orange"])
        Puck(Vec2D(6.0, 2.5), 0.45, 0.3)
        Puck(Vec2D(7.5, 2.5), 0.65, 0.3) 
        Puck(Vec2D(2.5, 5.5), 1.65, 0.3)
        Puck(Vec2D(7.5, 7.5), 0.95, 0.3)
    
    elif demo == 2:
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
        g.env.d2_state_cnt = len(initial_states)

        state = initial_states[g.env.demo2_variation_index]
        print("Variation", g.env.demo2_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"])

        p1 = Puck(Vec2D(2.0, 2.0), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        
        p2 = Puck(Vec2D(8.0, 6.75), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]

        spring_strength_Npm2 = 20.0
        spring_length_m = 1.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.15, c_damp=50.0, color=THECOLORS["yellow"])
    
        g.game_window.update_caption( g.game_window.caption + 
            f"     Variation {g.env.demo2_variation_index + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f})"
        )

    elif demo == 3:
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
        g.env.d3_state_cnt = len(initial_states)

        state = initial_states[g.env.demo3_variation_index]
        print("Variation", g.env.demo3_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"],
              "   p3_rps =", state["p3"]["rps"])
        
        p1p3_y_m = 2.3
        p1 = Puck(Vec2D(2.0, p1p3_y_m), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        p1.b2d_body.fixtures[0].friction = 2.0
        
        p3 = Puck(Vec2D(8.0, p1p3_y_m), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p3"]["color"])
        p3.b2d_body.angularVelocity = state["p3"]["rps"]
        p3.b2d_body.fixtures[0].friction = 2.0

        # Some equilateral triangle math:  h = (1/2) * √3 * a
        y_m = p1.pos_2d_m.y + (p3.pos_2d_m.x - p1.pos_2d_m.x) * 3**0.5 / 2.0
        x_m = p1.pos_2d_m.x + (p3.pos_2d_m.x - p1.pos_2d_m.x)/2.0
        p2 = Puck(Vec2D(x_m, y_m), 1.2, 1.0, CR_fixed=True, coef_rest=0.0, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]
        p2.b2d_body.fixtures[0].friction = 2.0

        spring_strength_Npm2 = 15.0
        spring_length_m = 1.0
        spring_width_m = 0.10
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p1, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_damp=50.0, color=THECOLORS["yellow"])

        g.game_window.update_caption( g.game_window.caption + 
            f"     Variation {g.env.demo3_variation_index + 1}" +
            f"     rps = ({state['p1']['rps']:.1f}, {state['p2']['rps']:.1f}, {state['p3']['rps']:.1f})"
        )

    elif demo == 4:
        spacing_factor = 1.0
        grid_size = 10,5
        for j in range(grid_size[0]):
            for k in range(grid_size[1]):
                if ((j,k) == (2,2)):
                    puck_color_value = THECOLORS["orange"]
                else:
                    puck_color_value = THECOLORS["grey"]

                offset_2d_m = Vec2D(0.0, 4.5)
                spacing_factor = 0.7
                position_2d_m = Vec2D(spacing_factor*(j+1), spacing_factor*(k+1)) + offset_2d_m

                Puck(position_2d_m, radius_m=0.25, density_kgpm2=1.0, 
                           color=puck_color_value,
                           CR_fixed=True, coef_rest=0.8, friction=0.05, friction_fixed=True)

        Wall(Vec2D(4.0, 4.5), half_width_m=4.0, half_height_m=0.04, angle_radians=-2*(math.pi/180), border_px=0)
        Wall(Vec2D(7.0, 2.5), half_width_m=3.0, half_height_m=0.04, angle_radians=+2*(math.pi/180), border_px=0)
    
    elif demo == 5:
        p1 = Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        p2 = Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
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

    elif demo == 7:        
        density = 0.8
        #                              , r_m , density
        tempPuck = Puck(Vec2D(4.0, 1.0), 0.55, density, color=THECOLORS["orange"], show_health=True, hit_limit=10)
        Spring(tempPuck, Vec2D(4.0, 1.0), strength_Npm=300.0, width_m=0.02, c_drag = 1.5)
        
        puck_position = Vec2D(0.0, g.game_window.UR_2d_m.y) + Vec2D(2.0, -2.0) # starting from upper left
        tempPuck = Puck(puck_position, 1.4, density, rect_fixture=True, aspect_ratio=0.1, show_health=True)
        tempPuck.b2d_body.angularVelocity = 0.5
        Spring(tempPuck, puck_position, strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)

        puck_position = Vec2D(8.5, 4.0)
        tempPuck = Puck(puck_position, 1.4, density, rect_fixture=True, aspect_ratio=0.1, show_health=True)
        tempPuck.b2d_body.angularVelocity = 0.5
        Spring(tempPuck, puck_position, strength_Npm=300.0, width_m=0.02, c_drag = 1.5 + 10.0)

        # Make some pinned-spring pucks.
        for m in range(0, 6): 
            pinPoint_2d = Vec2D(2.0 + (m * 0.65), 4.0)
            tempPuck = Puck(pinPoint_2d, 0.25, density, color=THECOLORS["orange"], show_health=True, hit_limit=15)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # Make user/client controllable pucks
        # for all the clients.
        y_puck_position_m = 1.0
        for client_name in g.env.clients:
            client = g.env.clients[client_name]
            if client.active and not client.drone:
                # Box2D drag modeling is slightly different than that in the circular engines. So, c_drag set higher than the default value, 0.7.
                g.air_table.buildControlledPuck( x_m=6.4, y_m=y_puck_position_m, r_m=0.45, client_name=client_name, sf_abs=False, c_drag=1.5)
                y_puck_position_m += 1.2
                        
        # drone pucks
        client_name = "C5"
        g.env.clients[client_name].active = True
        g.env.clients[client_name].drone = True
        g.air_table.buildControlledPuck( x_m=1.0, y_m=1.0, r_m=0.55, client_name=client_name, sf_abs=False)
        client_name = "C6"
        g.env.clients[client_name].active = True
        g.env.clients[client_name].drone = True
        g.air_table.buildControlledPuck( x_m=8.5, y_m=7.0, r_m=0.55, client_name=client_name, sf_abs=False)

        g.env.set_gravity("off")
            
    elif demo == 8:
        g.air_table.makeJello_variations()

    elif demo == 9:
        g.air_table.buildJelloGrid( angle=45, speed=0, pos_initial_2d_m=Vec2D(4.0, 2.5), puck_drag=1.5, show_health=True, coef_rest=0.85)

        g.env.clients["C5"].active = True
        g.env.clients["C5"].drone = True
        g.air_table.buildControlledPuck( x_m=2.0, y_m=8.0, r_m=0.45, client_name="C5")

        g.env.clients["C6"].active = True
        g.env.clients["C6"].drone = True
        g.air_table.buildControlledPuck( x_m=8.5, y_m=1.5, r_m=0.45, client_name="C6")

        # Pin two corners of the jello grid.
        Spring(g.air_table.pucks[ 1], Vec2D(0.3, 0.3), length_m=0.0, strength_Npm=800.0, width_m=0.02)
        Spring(g.air_table.pucks[10], Vec2D(9.7, 8.4), length_m=0.0, strength_Npm=800.0, width_m=0.02)

        g.env.set_gravity("off")
    
    elif demo == 0:
        density = 0.7
        width_m = 0.01
        aspect_ratio = 9.0
        x_position_m = 0.3
        for j in range(0, 9):
            y_puck_position_m = (width_m * aspect_ratio) + 0.01
            Puck(Vec2D(x_position_m, y_puck_position_m), width_m, density, rect_fixture=True, aspect_ratio=aspect_ratio, angle_r=0)
            width_m *= 1.5
            x_position_m *= 1.5

        # Drop a circular instigator with some spin, to get the chain reaction started.
        Puck(Vec2D(0.1, 0.2), 0.06, density, rect_fixture=False, angularVelocity_rps=-10)
        
        g.env.set_gravity("on")

    else:
        print("Nothing set up for this key.")

#============================================================
# Main procedural script.
#============================================================

def main():
    g.make_some_pucks = make_some_pucks
    game_loop = GameLoop(engine_type="box2d")
    game_loop.start(demo_index=7)

#============================================================
# start everything...
#============================================================

if __name__ == '__main__':
    main()
