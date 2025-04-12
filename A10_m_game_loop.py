#!/usr/bin/env python3

# Filename: A10_m_game_loop.py

"""
Game Loop Management for Air Table Physics Simulation

This module provides a unified game loop implementation for different air table physics engines.
It handles initialization, updates, and rendering for the simulation, supporting multiple physics
engines and network play.

The GameLoop class encapsulates all the common functionality needed by the primary 
script, A10_baseline_server.py, including:

Features:
    - Flexible physics engine selection (circular, other...)
    - Frame rate control and timing management
    - Network server setup and client handling
    - Input processing from local and network users
    - Physics calculations and collision detection
    - Rendering and display management
    - Demo state management and transitions

Classes:
    GameLoop: Main class that manages the game loop and simulation state

Usage:
    game_loop = GameLoop(engine_type="circular")
    game_loop.start(demo_index=7)  # Start with specified demo
"""

import platform, subprocess
import socket, math
import pygame

from A08_network import GameServer
from A10_m_air_table import CircularAirTable
from A10_m_environment import Client, GameWindow, Environment, signInOut_function, custom_update
# Global variables shared across scripts
import A10_m_globals as g

class GameLoop:
    # window dimensions: (width_px, height_px)
    def __init__(self, engine_type="circular", window_width_px=800, 
                 make_some_pucks=None, version="10"):
        self.make_some_pucks = make_some_pucks

        # Demos are best at an aspect ratio of 8/7.
        aspect_ratio_wh = 8/7 # width/height
        window_dimensions_px = (window_width_px, math.ceil(window_width_px / aspect_ratio_wh))
        
        pygame.init()
        
        # Create the first user/client and the methods for translating between screen and world.  
        # The 10 parameter is in meters and indicates the the width of the world and establishes the
        # relationship between screen pixels and world meters. Similar to the aspect ratio, currently, the
        # positioning of the objects in the demos is best if this stays at 10.
        self.env = Environment(window_dimensions_px, 10.0)
        g.env = self.env

        self.game_window = GameWindow('Air Table Server')
        g.game_window = self.game_window

        # Define the Left, Right, Bottom, and Top boundaries of the game window.
        walls_dic = {"L_m":0.0, "R_m":self.game_window.UR_2d_m.x, "B_m":0.0, "T_m":self.game_window.UR_2d_m.y}
        
        # Create appropriate air table type based on engine choice.
        if engine_type == "circular":
            self.air_table = CircularAirTable(walls_dic, version=version)
        else:
            raise ValueError(f"Unknown engine type: {engine_type}")
        g.air_table = self.air_table

        self.myclock = pygame.time.Clock()

        # Extend the clients dictionary to accommodate up to 10 network clients.
        for m in range(1,11):
            c_name = f'C{m}'
            self.env.clients[ c_name] = Client( self.env.client_colors[ c_name])
        
        # Font object for rendering text onto display surface.
        self.fnt_gameTimer = pygame.font.SysFont("Courier", 50)
        self.fnt_generalTimer = pygame.font.SysFont("Courier", 25)

        self.server = None
                    
    def start(self, demo_index=7):
        # Initialize demo
        self.make_some_pucks(demo_index)
        g.game_window.update_caption()
        
        # Setup network server
        self._setup_network_server()
        
        # Main loop
        while True:
            demo_index = self.update_air_table(demo_index)
            
    def _setup_network_server(self):
        # Setup network server.
        if platform.system() == 'Linux':
            local_ip = subprocess.check_output(["hostname", "-I"]).decode().strip()
        else:
            local_ip = socket.gethostbyname(socket.gethostname())
        print("Server IP address:", local_ip)
        
        self.server = GameServer(
            host='0.0.0.0', 
            port=8888,
            # Pygame uses a tuple and the network module does not use Vec2D.
            window_xy_px=g.env.screenSize_2d_px.tuple(), 
            update_function=custom_update,
            clientStates=self.env.clients,
            signInOut_function=signInOut_function
        )

    def update_air_table(self, demo_index):
        # Limit the framerate, but let it float below this limit.
        if (self.env.timestep_fixed):
            gameLoop_FR_limit = int(1.0/self.env.constant_dt_s)
        else:
            gameLoop_FR_limit = 480 # default
        
        self.env.tickCount += 1 # tickCount is reset to zero when demos start in make_some_pucks
        dt_gameLoop_s = self.myclock.tick(gameLoop_FR_limit) * 1e-3
        
        if (self.env.timestep_fixed):
            self.air_table.dt_s = self.env.constant_dt_s
        else:
            if self.air_table.engine == "circular-perfectKiss":
                self.air_table.dt_s = dt_gameLoop_s * self.air_table.timeDirection
            else:
                self.air_table.dt_s = dt_gameLoop_s
        
        # Get input from local user.
        resetmode = self.env.get_local_user_input(demo_index)
        
        # This check avoids instability when cpu is overloaded or when 
        # dragging the game window.
        if ((dt_gameLoop_s < 0.10) and (not self.air_table.stop_physics)):
            
            # Reset the game based on local user control.
            if resetmode in ["1p","2p","3p",0,1,2,3,4,5,6,7,8,9]:
                demo_index = resetmode
                print(demo_index)
                
                # Start, or restart a demo.
                self.make_some_pucks(demo_index)
                g.game_window.update_caption()
                        
            if (self.env.render_timer_s > self.env.dt_render_limit_s):
                # Get input from network clients.
                if self.server.running:
                    self.server.accept_clients()
                
                # Control the zoom
                self.env.control_zoom_and_view()
                
                # Demonstrate the client control of raw tubes.
                for tube in self.air_table.raw_tubes:
                    tube.client_rotation_control()

                for controlled_puck in self.air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    controlled_puck.jet.client_rotation_control()
                    # Control jets and calculate forces on pucks.
                    controlled_puck.jet.turn_jet_forces_onoff()
                    
                    if controlled_puck.gun:
                        controlled_puck.gun.client_rotation_control()
                        # Turn gun on/off
                        controlled_puck.gun.control_firing()
                        # Turn shield on/off
                        controlled_puck.gun.control_shield()
            
            # Calculate client related cursor-string forces.
            for client_name in self.env.clients:
                self.env.clients[client_name].calc_string_forces_on_pucks()
            
            # Calculate spring forces on pucks.
            for eachspring in self.air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            # Apply forces to the pucks and calculate movements.
            for eachpuck in self.air_table.pucks:
                eachpuck.calc_regularDragForce()
                self.air_table.update_TotalForce_Speed_Position(eachpuck)
            
            # Check for puck-wall and puck-puck collisions and make penetration corrections.
            self.air_table.check_for_collisions()

            if self.air_table.FPS_display and (self.env.tickCount > 10):
                self.env.fr_avg.update(1.0/abs(self.air_table.dt_s))
            
            if (self.env.render_timer_s > self.env.dt_render_limit_s):
                # Erase the blackboard.
                if not self.env.inhibit_screen_clears:
                    if (not self.air_table.correct_for_puck_penetration):
                        yellow_level = 50
                        self.game_window.surface.fill((yellow_level,yellow_level,0))
                    else:
                        if not self.air_table.g_ON:
                            self.game_window.surface.fill((0,0,0))  # black
                        else:
                            self.game_window.surface.fill((20,20,70))  # dark blue

                # Display the physics cycle rate.
                if self.air_table.FPS_display:
                    self.env.fr_avg.draw( self.game_window.surface, 10, 10, caution=self.env.timestep_fixed)
                
                # Clean out old bullets.
                for thisPuck in self.air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and (thisPuck.groupIndex != 0) and ((self.air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        thisPuck.delete()

                self.env.remove_healthless_pucks()
                
                # Draw pucks, springs, mouse tethers, guns, and jets.
                self.air_table.draw()

                for eachpuck in self.air_table.pucks:
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if eachpuck.jet.client.active:
                            if eachpuck.gun: eachpuck.gun.draw_shield()
                            eachpuck.jet.draw()
                            if eachpuck.gun: eachpuck.gun.draw()

                # For a few demos that use raw tubes.            
                for tube in self.air_table.raw_tubes:
                    tube.draw_tube()

                for eachspring in self.air_table.springs: 
                    eachspring.draw()
                
                # Draw cursors for network clients.
                for client_name in self.env.clients:
                    client = self.env.clients[client_name]
                    client.draw_cursor_string()
                    
                    if (client.active and not client.drone):
                        client.draw_fancy_server_cursor()
                    
                self.env.render_timer_s = 0
            
            # Renders noticeably smoother (on my Windows computer) if flip is called at the 
            # rate of the main loop (more frequently than the render_timer block above).
            pygame.display.flip()

            # Update the rendering timer. This is used to limit the rendering framerate to be 
            # below that of the physics calculations.
            self.env.render_timer_s += dt_gameLoop_s
            
            # Keep track of time for use in timestamp operations
            # (determine the age of old bullets to be deleted)
            self.air_table.time_s += self.air_table.dt_s
            
        return demo_index
