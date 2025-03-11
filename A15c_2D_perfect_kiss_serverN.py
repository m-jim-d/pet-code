#!/usr/bin/env python3

# Filename: A15c_2D_perfect_kiss_serverN.py

import random

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Puck, Spring
from A15_game_loop import GameLoop

import A15_globals as g

#===========================================================
# Functions
#===========================================================

def setup_pool_shot():
    g.env.timestep_fixed = True
    g.env.constant_dt_s = 1/20.0
    
    g.air_table.inhibit_wall_collisions = True
    g.env.inhibit_screen_clears = True
    
    # Randomize the starting x position of the incoming puck. Elastic pucks make it reversible.
    Puck(Vec2D(random.random()-0.3, 4.80), 0.45, 0.3, color=THECOLORS["orange"], coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(  25.0, 0.0))
    Puck(Vec2D(4.0,                 4.30), 0.45, 0.3,                            coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(   0.0, 0.0))
       
def make_some_pucks(demo):
    g.game_window.update_caption("Perfect Kiss Air-Table Server A15c     Demo #" + str(demo))
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
    g.air_table.coef_rest = 1.00
    g.air_table.time_s = 0.0
    
    g.env.inhibit_screen_clears = False
    g.air_table.inhibit_wall_collisions = False
    g.air_table.correct_for_wall_penetration = True
    g.air_table.correct_for_puck_penetration = True
    
    g.air_table.collision_count = 0
    g.air_table.count_direction = 1
    g.air_table.timeDirection = 1

    g.air_table.perfect_kiss = False
    
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
        spring_drag = 0.5 # 0.0
        spring_damper = 5.0

        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["red"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["tan"])
        Spring(p3, p1, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["gold"])

    elif demo == 7:
        g.air_table.coef_rest = 1.00
        
        # Make user/client controllable pucks for all the active clients.
        y_position_m = 1.0
        
        # Drone clients.
        g.env.clients["C5"].active = True
        g.env.clients["C5"].drone = True
        g.env.clients["C6"].active = True
        g.env.clients["C6"].drone = True
        
        # Arrange human-controlled pucks in a column.
        for name in g.env.clients:
            client = g.env.clients[name]
            if client.active and (not client.drone):
                g.air_table.buildControlledPuck( x_m=7.0, y_m=y_position_m, r_m=0.45, client_name=name, sf_abs=False)
                y_position_m += 1.3
        
        # Position the drone-controlled pucks in specific locations.      
        g.air_table.buildControlledPuck( x_m=3.0, y_m=7.0, r_m=0.55, client_name="C5", sf_abs=False)  
        g.air_table.buildControlledPuck( x_m=3.0, y_m=1.0, r_m=0.55, client_name="C6", sf_abs=False)
        
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
                    
    elif demo == 8:
        g.air_table.throwJello_variations()  # Variations handled within method

    elif demo == 9:
        g.air_table.targetJello_variations()

    elif demo == '1p':
        g.env.demo_variations['1p']['count'] = 1  # Basic pool shot, no penetration correction, no perfect kiss
        g.air_table.correct_for_puck_penetration = False
        g.air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '2p':
        g.env.demo_variations['2p']['count'] = 1  # Pool shot with penetration correction only
        g.air_table.correct_for_puck_penetration = True
        g.air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '3p':
        g.env.demo_variations['3p']['count'] = 1  # Pool shot with both penetration correction and perfect kiss
        g.air_table.correct_for_puck_penetration = True
        g.air_table.perfect_kiss = True
        setup_pool_shot()
        
    else:
        print("Nothing set up for this key.")

#============================================================
# Main procedural script.
#============================================================

def main():
    g.make_some_pucks = make_some_pucks
    game_loop = GameLoop(engine_type = "circular-perfectKiss")
    game_loop.start(demo_index=7)

#============================================================
# Run main().  
#============================================================
        
if __name__ == '__main__':
    main()
#!/usr/bin/env python3

# Filename: A15c_2D_perfect_kiss_serverN.py

import random

from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A15_air_table_objects import Puck, Spring
from A15_game_loop import GameLoop

import A15_globals as g

#===========================================================
# Functions
#===========================================================

def setup_pool_shot():
    g.env.timestep_fixed = True
    g.env.constant_dt_s = 1/20.0
    
    g.air_table.inhibit_wall_collisions = True
    g.env.inhibit_screen_clears = True
    
    # Randomize the starting x position of the incoming puck. Elastic pucks make it reversible.
    Puck(Vec2D(random.random()-0.3, 4.80), 0.45, 0.3, color=THECOLORS["orange"], coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(  25.0, 0.0))
    Puck(Vec2D(4.0,                 4.30), 0.45, 0.3,                            coef_rest=1.0, CR_fixed=True, vel_2d_mps=Vec2D(   0.0, 0.0))
       
def make_some_pucks(demo):
    g.game_window.update_caption("Perfect Kiss Air-Table Server A15c     Demo #" + str(demo))
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
    g.air_table.coef_rest = 1.00
    g.air_table.time_s = 0.0
    
    g.env.inhibit_screen_clears = False
    g.air_table.inhibit_wall_collisions = False
    g.air_table.correct_for_wall_penetration = True
    g.air_table.correct_for_puck_penetration = True
    
    g.air_table.collision_count = 0
    g.air_table.count_direction = 1
    g.air_table.timeDirection = 1

    g.air_table.perfect_kiss = False
    
    # Each demo will have a single variation unless specified below.
    g.env.demo_variations[demo]['count'] = 1  # Single variation
    
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
        spring_drag = 0.5 # 0.0
        spring_damper = 5.0

        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["red"])
        Spring(p2, p3, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["tan"])
        Spring(p3, p1, spring_length_m, spring_strength_Npm2, width_m=spring_width_m, 
            c_drag=spring_drag, c_damp=spring_damper, color=THECOLORS["gold"])

    elif demo == 7:
        g.air_table.coef_rest = 1.00
        
        # Make user/client controllable pucks for all the active clients.
        y_position_m = 1.0
        
        # Drone clients.
        g.env.clients["C5"].active = True
        g.env.clients["C5"].drone = True
        g.env.clients["C6"].active = True
        g.env.clients["C6"].drone = True
        
        # Arrange human-controlled pucks in a column.
        for name in g.env.clients:
            client = g.env.clients[name]
            if client.active and (not client.drone):
                g.air_table.buildControlledPuck( x_m=7.0, y_m=y_position_m, r_m=0.45, client_name=name, sf_abs=False)
                y_position_m += 1.3
        
        # Position the drone-controlled pucks in specific locations.      
        g.air_table.buildControlledPuck( x_m=3.0, y_m=7.0, r_m=0.55, client_name="C5", sf_abs=False)  
        g.air_table.buildControlledPuck( x_m=3.0, y_m=1.0, r_m=0.55, client_name="C6", sf_abs=False)
        
        # Make some pucks that are not controllable.
        density = 0.7
        
        # Make a horizontal row of pinned-spring pucks.
        for m in range(0, 6): 
            pinPoint_2d = Vec2D(2.0 + (m * 0.65), 4.5)
            tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # Make a vertical column of pinned-spring pucks.
        for m in range(-3, 4):
            pinPoint_2d = Vec2D(2 + 6*0.65, 4.5 + m*0.65)
            tempPuck = Puck( pinPoint_2d, 0.25, density, color=THECOLORS["orange"], hit_limit=20, show_health=True)
            Spring(tempPuck, pinPoint_2d, strength_Npm=300.0, width_m=0.02, c_drag=1.5)
        
        # One free standing puck
        Puck( Vec2D(9.0, 4.5), 0.7, density, color=THECOLORS["cyan"], hit_limit=20, c_drag=0.7, show_health=True)
                    
    elif demo == 8:
        g.air_table.throwJello_variations()

    elif demo == 9:
        g.air_table.targetJello_variations()
        
    elif demo == '1p':
        g.air_table.correct_for_puck_penetration = False
        g.air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '2p':
        g.air_table.correct_for_puck_penetration = True
        g.air_table.perfect_kiss = False
        setup_pool_shot()
        
    elif demo == '3p':
        g.air_table.correct_for_puck_penetration = True
        g.air_table.perfect_kiss = True
        setup_pool_shot()
        
    else:
        print("Nothing set up for this key.")

#============================================================
# main procedural script
#============================================================

def main():
    g.make_some_pucks = make_some_pucks
    game_loop = GameLoop(engine_type = "circular-perfectKiss")
    game_loop.start(demo_index=7)

#============================================================
# Start everything.  
#============================================================
        
if __name__ == '__main__':
    main()
