#!/usr/bin/env python3

# Filename: A15a_2D_finished_game.py

import socket
import platform, subprocess

import pygame
from pygame.color import THECOLORS

from A09_vec2d import Vec2D
from A08_network import GameServer
from A15_air_table import CircularAirTable
from A15_air_table_objects import Puck, Spring
from A15_environment import Client, GameWindow, Environment, signInOut_function, custom_update

import A15_globals as A_g

#===========================================================
# Functions
#===========================================================
        
def make_some_pucks(demo):
    game_window.update_caption("Air-Table Server A15a     Demo #" + str(demo))
    env.fr_avg.reset()
    air_table.coef_rest = 1.00
    env.tickCount = 0
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
        Puck(Vec2D(2.00, 3.00),  0.4, 0.3)
        Puck(Vec2D(3.50, 4.50),  0.4, 0.3)
        
        spring_strength_Npm2 = 20.0 #18.0
        spring_length_m = 1.5
        Spring(air_table.pucks[0], air_table.pucks[1], spring_length_m, spring_strength_Npm2, width_m=0.2)
    
    elif demo == 6:
        Puck(Vec2D(2.00, 3.00),  0.65, 0.3) 
        Puck(Vec2D(3.50, 4.50),  0.65, 0.3) 
        Puck(Vec2D(5.00, 3.00),  0.65, 0.3) 
        
        # No springs on this one.
        Puck(Vec2D(3.50, 7.00),  0.95, 0.3) 
    
        spring_strength_Npm2 = 200.0 #18.0
        spring_length_m = 2.5
        spring_width_m = 0.07
        Spring(air_table.pucks[0], air_table.pucks[1],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
        Spring(air_table.pucks[1], air_table.pucks[2],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
        Spring(air_table.pucks[2], air_table.pucks[0],
              spring_length_m, spring_strength_Npm2, width_m=spring_width_m)
    
    elif demo == 7:
        air_table.coef_rest = 1.00
        
        # Make user/client controllable pucks for all the active clients.
        y_position_m = 1.0
        
        # Drone clients.
        env.clients["C5"].active = True
        env.clients["C5"].drone = True
        env.clients["C6"].active = True
        env.clients["C6"].drone = True
        
        # Arrange human-controlled pucks in a column.
        for name in env.clients:
            client = env.clients[name]
            if client.active and (not client.drone):
                air_table.buildControlledPuck( x_m=7.0, y_m=y_position_m, r_m=0.45, client_name=name, sf_abs=False)
                y_position_m += 1.3
        
        # Position the drone-controlled pucks in specific locations.      
        air_table.buildControlledPuck( x_m=3.0, y_m=7.0, r_m=0.55, client_name="C5", sf_abs=False)  
        air_table.buildControlledPuck( x_m=3.0, y_m=1.0, r_m=0.55, client_name="C6", sf_abs=False)
        
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
        air_table.makeJello_variations()

    elif demo == 9:
        air_table.coef_rest = 1.00
        
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

    window_dimensions_px = (800, 700)   # window_width_px, window_height_px

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.
    A_g.env = env

    game_window = GameWindow(window_dimensions_px, 'Air Table Server')
    A_g.game_window = game_window

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    air_table = CircularAirTable({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})
    A_g.air_table = air_table
    A_g.engine_type = "circular"

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
        
        # Get input from network clients.
        
        # This dt check avoids problem when dragging the game window.
        if ((dt_physics_s < 0.10) and (not air_table.stop_physics)):
            
            # Reset the game based on local user control.
            if resetmode in [0,1,2,3,4,5,6,7,8,9]:
                demo_index = resetmode
                print(demo_index)
                
                # This should remove all references to the pucks and effectively delete them. 
                air_table.pucks = []
                air_table.controlled_pucks = []
                air_table.target_pucks = []
                air_table.springs = []
                
                # Now just black out the screen.
                game_window.clear()
                
                # Reinitialize the demo or start a new one.
                make_some_pucks( demo_index)               
                        
            if (env.render_timer_s > env.dt_render_limit_s):
                # Get input from network clients.
                if server.running:
                    server.accept_clients()
                
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
                    
                    # Turn jet on/off
                    controlled_puck.jet.turn_jet_forces_onoff()

                    # Turn gun on/off
                    controlled_puck.gun.control_firing()
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield()                    
            
            # Calculate forces on the pucks.
            # Cursor strings (spring)
            for client_name in env.clients:
                env.clients[client_name].calc_string_forces_on_pucks()
                
            # Drag on puck movement.
            for eachpuck in air_table.target_pucks:
                eachpuck.calc_regularDragForce()            
            
            # General spring forces.
            for eachspring in air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in air_table.pucks:
                air_table.update_PuckSpeedAndPosition( eachpuck, dt_physics_s)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            air_table.check_for_collisions()
            
            if air_table.FPS_display and env.tickCount > 10:
                env.fr_avg.update(1.0/dt_physics_s)
            
            if (env.render_timer_s > env.dt_render_limit_s):
                
                # Erase the blackboard.
                if not air_table.g_ON:
                    game_window.surface.fill((0,0,0))  # black
                else:
                    game_window.surface.fill((20,20,70))  # dark blue
                
                #print(f"{len(air_table.target_pucks)}, {len(air_table.controlled_pucks)}, {len(air_table.pucks)}, s:{len(air_table.springs)}")

                # Clean out old bullets.
                for thisPuck in air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and ((air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        air_table.pucks.remove( thisPuck)
                
                # Display the physics cycle rate.
                if air_table.FPS_display:
                    env.fr_avg.draw( game_window.surface, 10, 10, caution=env.timestep_fixed)
                
                # Display timers.
                if (demo_index == 8):
                    game_window.display_number(air_table.game_time_s, fnt_gameTimer, mode='gameTimer')
                
                # Now draw pucks, springs, mouse tethers, and jets.
                # Draw boundaries of table.
                air_table.draw()
                
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
            
            pygame.display.flip()

            # Limit the rendering framerate to be below that of the physics calculations.
            env.render_timer_s += dt_physics_s
            
            # Keep track of time for deleting old bullets.
            air_table.time_s += dt_physics_s
            
            # Jello madness game timer
            if air_table.tangled:
                air_table.game_time_s += dt_physics_s
                
#============================================================
# Run main().  
#============================================================
        
main()