#!/usr/bin/env python3

# Filename: A16c_2D_B2D_serverN.py

import math
import socket
import platform, subprocess

import pygame
from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A08_network import GameServer
from A15_air_table import Box2DAirTable
from A15_air_table_objects import Wall, Puck, Spring
from A15_environment import Client, GameWindow, Environment, signInOut_function, custom_update

import A15_globals as A_g

#===========================================================
# Functions
#===========================================================
        
def make_some_pucks(demo):
    game_window.update_caption("PyBox2D Air-Table Server A16c     Demo #" + str(demo))
    env.timestep_fixed = False

    # This removes all references to pucks and walls and effectively deletes them. 
    for eachpuck in air_table.pucks[:]:
        eachpuck.delete()
    for eachWall in air_table.walls[:]:
        if not eachWall.fence:
            eachWall.delete()

    # Most of the demos don't need the tangle checker.
    air_table.jello_tangle_checking_enabled = False
    
    # Now just black out the screen.
    game_window.clear()

    env.fr_avg.reset()
    env.tickCount = 0

    for client_name in env.clients:
        client = env.clients[client_name]
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
        env.d2_state_cnt = len(initial_states)

        state = initial_states[env.demo2_variation_index]
        print("Variation", env.demo2_variation_index + 1, 
              "   p1_rps =", state["p1"]["rps"], 
              "   p2_rps =", state["p2"]["rps"])

        p1 = Puck(Vec2D(2.0, 2.0), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p1"]["color"])
        p1.b2d_body.angularVelocity = state["p1"]["rps"]
        
        p2 = Puck(Vec2D(8.0, 6.75), 1.7, 1.0, CR_fixed=True, coef_rest=0.0, friction=2.0, friction_fixed=True, border_px=10, color=state["p2"]["color"])
        p2.b2d_body.angularVelocity = state["p2"]["rps"]

        spring_strength_Npm2 = 20.0
        spring_length_m = 1.0
        Spring(p1, p2, spring_length_m, spring_strength_Npm2, width_m=0.15, c_damp=50.0, color=THECOLORS["yellow"])
    
        game_window.update_caption( game_window.caption + 
            f"     Variation {env.demo2_variation_index + 1}" +
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
        env.d3_state_cnt = len(initial_states)

        state = initial_states[env.demo3_variation_index]
        print("Variation", env.demo3_variation_index + 1, 
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

        game_window.update_caption( game_window.caption + 
            f"     Variation {env.demo3_variation_index + 1}" +
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
        Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
        density = 1.5
        radius = 0.7
        
        coef_rest_puck = 0.3
        
        spring_strength_Npm2 = 400.0
        spring_length_m = 2.5
        spring_width_m = 0.07
        spring_drag = 0.0
        spring_damper = 5.0

        Puck(Vec2D(2.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        Puck(Vec2D(3.50, 4.50),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        Puck(Vec2D(5.00, 3.00),  radius, density, coef_rest=coef_rest_puck, CR_fixed=True)
        
        # No springs on this one.
        Puck(Vec2D(3.50, 7.00),  0.95, density, coef_rest=coef_rest_puck, CR_fixed=True)
        
        Spring(air_table.pucks[0], air_table.pucks[1],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        Spring(air_table.pucks[1], air_table.pucks[2],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        Spring(air_table.pucks[2], air_table.pucks[0],
               spring_length_m, spring_strength_Npm2, width_m=spring_width_m, c_drag=spring_drag)
        
        # Increase the shock-absorber strength for each spring.
        for spring in air_table.springs:                                 
            spring.damper_Ns2pm2 = spring_damper
                
    elif demo == 7:        
        density = 0.8
        #                              , r_m , density
        tempPuck = Puck(Vec2D(4.0, 1.0), 0.55, density, color=THECOLORS["orange"], show_health=True, hit_limit=10)
        Spring(tempPuck, Vec2D(4.0, 1.0), strength_Npm=300.0, width_m=0.02, c_drag = 1.5)
        
        puck_position = Vec2D(0.0, game_window.UR_2d_m.y) + Vec2D(2.0, -2.0) # starting from upper left
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
        for client_name in env.clients:
            client = env.clients[client_name]
            if client.active and not client.drone:
                air_table.buildControlledPuck( x_m=6.4, y_m=y_puck_position_m, r_m=0.45, client_name=client_name, sf_abs=False)
                y_puck_position_m += 1.2
                        
        # drone pucks
        client_name = "C5"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=1.0, y_m=1.0, r_m=0.55, client_name=client_name, sf_abs=False)
        client_name = "C6"
        env.clients[client_name].active = True
        env.clients[client_name].drone = True
        air_table.buildControlledPuck( x_m=8.5, y_m=7.0, r_m=0.55, client_name=client_name, sf_abs=False)

        env.set_gravity("off")
            
    elif demo == 8:
        air_table.makeJello_variations()

    elif demo == 9:
        air_table.buildJelloGrid( angle=45, speed=0, pos_initial_2d_m=Vec2D(4.0, 2.5), puck_drag=1.5, show_health=True, coef_rest=0.85)

        env.clients["C5"].active = True
        env.clients["C5"].drone = True
        air_table.buildControlledPuck( x_m=2.0, y_m=8.0, r_m=0.45, client_name="C5")

        env.clients["C6"].active = True
        env.clients["C6"].drone = True
        air_table.buildControlledPuck( x_m=8.5, y_m=1.5, r_m=0.45, client_name="C6")

        # Pin two corners of the jello grid.
        Spring(air_table.pucks[ 1], Vec2D(0.3, 0.3), length_m=0.0, strength_Npm=800.0, width_m=0.02)
        Spring(air_table.pucks[10], Vec2D(9.7, 8.4), length_m=0.0, strength_Npm=800.0, width_m=0.02)

        env.set_gravity("off")
    
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
        
        env.set_gravity("on")

    else:
        print("Nothing set up for this key.")

#============================================================
# Main procedural script.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_table
    
    pygame.init()

    myclock = pygame.time.Clock()

    window_dimensions_px = (800, 700)  # window_width_px, window_height_px
    
    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.
    A_g.env = env

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')
    A_g.game_window = game_window

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = Box2DAirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})
    A_g.air_table = air_table
    A_g.engine_type = "box2d"

    air_table.buildFence() # walls at the window boundaries.

    # Extend the clients dictionary to accommodate up to 10 network clients.
    for m in range(1,11):
        c_name = 'C' + str(m)
        env.clients[ c_name] = Client( env.client_colors[ c_name])
    
    # Font object for rendering text onto display surface.
    fnt_gameTimer = pygame.font.SysFont("Courier", 50)

    # Add some pucks to the table.
    demo_index = 7
    make_some_pucks( demo_index)

    # Setup network server.
    if platform.system() == 'Linux':
        local_ip = subprocess.check_output(["hostname", "-I"]).decode().strip()
    else:
        local_ip = socket.gethostbyname(socket.gethostname())
    print("Server IP address:", local_ip)

    server = GameServer(host='0.0.0.0', port=8888, 
                        update_function=custom_update, clientStates=env.clients, 
                        signInOut_function=signInOut_function)

    while True:
        # Limit the framerate, but let it float below this limit.
        if (env.timestep_fixed):
            gameLoop_FR_limit = int(1.0/env.constant_dt_s)
        else:
            gameLoop_FR_limit = 480 # default
        
        env.tickCount += 1 # tickCount is reset to zero when demos start in make_some_pucks
        dt_gameLoop_s = myclock.tick( gameLoop_FR_limit) * 1e-3
        
        if (env.timestep_fixed):
            dt_physics_s = env.constant_dt_s
        else:
            dt_physics_s = dt_gameLoop_s
        
        # Get input from local user.
        resetmode = env.get_local_user_input(demo_index)
        
        # This check avoids problem when dragging the game window.
        if ((dt_gameLoop_s < 0.10) and (not air_table.stop_physics)):
            
            # Reset the game based on local user control.
            if resetmode in [0,1,2,3,4,5,6,7,8,9]:
                demo_index = resetmode
                print(demo_index)
                                
                # Start, or restart a demo.
                make_some_pucks( demo_index)               
                        
            if (env.render_timer_s > env.dt_render_limit_s):
                # Get input from network clients.
                if server.running:
                    server.accept_clients()
                
            for client_name in env.clients:
                # Calculate client related forces.
                env.clients[client_name].calc_string_forces_on_pucks()
                
            if (env.render_timer_s > env.dt_render_limit_s):
                # Control the zoom
                env.control_zoom_and_view()
                
                for controlled_puck in air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    controlled_puck.jet.client_rotation_control()
                    
                    if env.clients[ controlled_puck.client_name].drone:
                        controlled_puck.gun.drone_rotation_control()
                    else:
                        controlled_puck.gun.client_rotation_control()
                    
                    # Turn gun on/off
                    controlled_puck.gun.control_firing()
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield()
            
            # Calculate jet forces on pucks...
            for controlled_puck in air_table.controlled_pucks:
                controlled_puck.jet.turn_jet_forces_onoff()
            
            # Calculate the forces the springs apply on the pucks...
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                eachpuck.calc_regularDragForce()
                air_table.update_TotalForceVectorOnPuck( eachpuck, dt_physics_s)
            
            # Run Box2d    
            air_table.b2d_world.Step( dt_physics_s, 10, 10)
            
            # Get new positions, translational velocities, and rotational speeds, from box2d
            for eachpuck in air_table.pucks:
                eachpuck.get_Box2d_XandV()
            
            # Check for puck-puck contact.
            if air_table.jello_tangle_checking_enabled:
                air_table.check_for_jello_tangle()

            if air_table.FPS_display and env.tickCount > 10:
                env.fr_avg.update(1.0/dt_physics_s) # 1.0/dt_physics_s myclock.get_fps()
            
            if (env.render_timer_s > env.dt_render_limit_s):
                
                # Erase the blackboard.
                if not env.inhibit_screen_clears:
                    if not air_table.g_ON:
                        game_window.surface.fill((0,0,0))  # black
                    else:
                        game_window.surface.fill((20,20,70))  # dark blue

                #print(f"{len(air_table.target_pucks)}, {len(air_table.controlled_pucks)}, {len(air_table.pucks)}, s:{len(air_table.springs)}")

                # Display the physics cycle rate.
                if air_table.FPS_display:
                    env.fr_avg.draw( game_window.surface, 10, 10, caution=env.timestep_fixed)
                    
                if (demo_index == 8):
                    game_window.display_number(air_table.game_time_s, fnt_gameTimer, mode='gameTimer')
                
                # Clean out old bullets.
                for thisPuck in air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and ((air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        thisPuck.delete()

                # Draw pucks, springs, mouse tethers, and jets.
                
                for eachWall in air_table.walls:
                    eachWall.draw()

                for eachpuck in air_table.pucks: 
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if eachpuck.jet.client.active:
                            eachpuck.gun.draw_shield()
                            eachpuck.jet.draw()
                            eachpuck.gun.draw()
                            
                for eachspring in air_table.springs: 
                    eachspring.draw()
                
                env.remove_healthless_pucks()
                
                for client_name in env.clients:
                    client = env.clients[client_name]
                    client.draw_cursor_string()
                    
                    # Draw cursors for network clients.
                    if (client.active and not client.drone):
                        client.draw_fancy_server_cursor()
                    
                env.render_timer_s = 0
            
            # Renders noticeably smoother (on my Windows computer) if flip is called at the 
            # rate of the main loop (more frequently than the render_timer block above).
            pygame.display.flip()

            # Limit the rendering framerate to be below that of the physics calculations.
            env.render_timer_s += dt_gameLoop_s
            
            # Keep track of time for use in timestamping operations
            # (determine the age of old bullets to be deleted)
            air_table.time_s += dt_gameLoop_s
            
            # Jello madness game timer
            if air_table.jello_tangle_checking_enabled:
                air_table.tangle_checker_time_s += dt_gameLoop_s
                if air_table.tangled:
                    air_table.game_time_s += dt_gameLoop_s
                
#============================================================
# Run main().  
#============================================================

main()
