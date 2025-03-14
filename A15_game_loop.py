#!/usr/bin/env python3

# Filename: A15_game_loop.py

"""
Game Loop Management for Air Table Physics Simulation

This module provides a unified game loop implementation for different air table physics engines.
It handles initialization, updates, and rendering for the simulation, supporting multiple physics
engines and network play.

The GameLoop class encapsulates all the common functionality needed by the three primary 
scripts (A15a, A15c, A16c), including:

Features:
    - Flexible physics engine selection (box2d, circular, circular-perfectKiss)
    - Frame rate control and timing management
    - Network server setup and client handling
    - Input processing from local and network users
    - Physics calculations and collision detection
    - Rendering and display management
    - Demo state management and transitions

Classes:
    GameLoop: Main class that manages the game loop and simulation state

Usage:
    game_loop = GameLoop(engine_type="box2d")  # or "circular" or "circular-perfectKiss"
    game_loop.start(demo_index=7)  # Start with specified demo
"""

import platform, subprocess
import socket, math
import pygame

from A08_network import GameServer, RunningAvg
from A15_air_table import Box2DAirTable, CircularAirTable, PerfectKissAirTable
from A15_environment import Client, GameWindow, Environment, signInOut_function, custom_update

# Global variables shared across scripts
import A15_globals as g

class GameLoop:
    # window dimensions: (width_px, height_px)
    def __init__(self, engine_type="box2d", window_width_px=800):
        # Demos are best at an aspect ratio of 8/7.        
        aspect_ration = 8/7 # width/height
        window_dimensions_px = (window_width_px, math.ceil(window_width_px / aspect_ration))
        
        pygame.init()
        
        # Create the first user/client and the methods for moving between the screen and the world.
        self.env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.
        g.env = self.env

        self.game_window = GameWindow('Air Table Server')
        g.game_window = self.game_window

        # Define the Left, Right, Bottom, and Top boundaries of the game window.
        walls_dic = {"L_m":0.0, "R_m":self.game_window.UR_2d_m.x, "B_m":0.0, "T_m":self.game_window.UR_2d_m.y}
        
        # Create appropriate air table type based on engine choice.
        if engine_type == "box2d":
            self.air_table = Box2DAirTable(walls_dic)
        elif engine_type == "circular":
            self.air_table = CircularAirTable(walls_dic)
        elif engine_type == "circular-perfectKiss":
            self.air_table = PerfectKissAirTable(walls_dic)
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

        self.pk_collision_cnt = RunningAvg(1, pygame, colorScheme='light')

        self.server = None
                    
    def start(self, demo_index=7):
        if (self.air_table.engine == "box2d"):
            self.air_table.buildFence() # walls at the window boundaries.

        # Initialize demo
        g.make_some_pucks(demo_index)
        
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
                g.make_some_pucks(demo_index)               
                        
            if (self.env.render_timer_s > self.env.dt_render_limit_s):
                # Get input from network clients.
                if self.server.running:
                    self.server.accept_clients()
                
                # Control the zoom
                self.env.control_zoom_and_view()
                
                for controlled_puck in self.air_table.controlled_pucks:
                    # Rotate based on keyboard of the controlling client.
                    controlled_puck.jet.client_rotation_control()
                    
                    if self.env.clients[ controlled_puck.client_name].drone:
                        controlled_puck.gun.drone_rotation_control()
                    else:
                        controlled_puck.gun.client_rotation_control()
                    # Control jets and calculate forces on pucks.
                    controlled_puck.jet.turn_jet_forces_onoff()
                    
                    # Turn gun on/off
                    controlled_puck.gun.control_firing()
                    
                    # Turn shield on/off
                    controlled_puck.gun.control_shield()
            
            # Calculate client related cursor-string forces.
            for client_name in self.env.clients:
                self.env.clients[client_name].calc_string_forces_on_pucks()

            if (self.air_table.engine != "box2d"):    
                # Drag on puck movement.
                for eachpuck in self.air_table.target_pucks:
                    eachpuck.calc_regularDragForce()
            
            # Calculate spring forces on pucks.
            for eachspring in self.air_table.springs:
                eachspring.calc_spring_forces_on_pucks()
                
            if (self.air_table.engine == "box2d"):
                # Apply forces to the pucks.
                for eachpuck in self.air_table.pucks:
                    self.air_table.update_TotalForceVectorOnPuck(eachpuck)
                
                # Advance Box2d by a single time step (dt). This calculate movements and
                # manages collisions.
                self.air_table.b2d_world.Step( self.air_table.dt_s, 10, 10)
                
                # Get new positions, translational velocities, and rotational speeds, from box2d
                for eachpuck in self.air_table.pucks:
                    eachpuck.get_Box2d_XandV()
                
                # Check for puck-puck contact (Jello tangle).
                if self.air_table.jello_tangle_checking_enabled:
                    self.air_table.check_for_jello_tangle()
            else:
                # Apply forces to the pucks and calculate movements.
                for eachpuck in self.air_table.pucks:
                    self.air_table.update_TotalForce_Speed_Position(eachpuck)
                
                # Check for puck-wall and puck-puck collisions and make penetration corrections.
                self.air_table.check_for_collisions()

            if self.air_table.FPS_display and (self.env.tickCount > 10):
                self.env.fr_avg.update(1.0/abs(self.air_table.dt_s))
            
            if (self.env.render_timer_s > self.env.dt_render_limit_s):
                # Erase the blackboard.
                if not self.env.inhibit_screen_clears:
                    if (self.air_table.engine == "circular-perfectKiss" and self.air_table.perfect_kiss):
                        gray_level = 40
                        self.game_window.surface.fill((gray_level,gray_level,gray_level))
                    else:
                        if not self.air_table.g_ON:
                            self.game_window.surface.fill((0,0,0))  # black
                        else:
                            self.game_window.surface.fill((20,20,70))  # dark blue

                #print(f"{len(self.air_table.target_pucks)}, {len(self.air_table.controlled_pucks)}, {len(self.air_table.pucks)}, s:{len(self.air_table.springs)}")

                # Display the physics cycle rate.
                if self.air_table.FPS_display:
                    self.env.fr_avg.draw( self.game_window.surface, 10, 10, caution=self.env.timestep_fixed)
                    
                # Display timers.
                if (demo_index == 8):
                    self.game_window.display_number(self.air_table.game_time_s, self.fnt_gameTimer, mode='gameTimer')
                
                # Display the collision count and timer for the demos where reversibility is well demonstrated.
                if (self.air_table.engine == "circular-perfectKiss") and self.air_table.perfect_kiss and (demo_index in [1,2,3,4]):
                    self.game_window.display_number(self.air_table.time_s, self.fnt_generalTimer, mode='generalTimer')
                    # Generally, counts up to 100 reverse well. Counts outside the range below will not display correctly.
                    self.pk_collision_cnt.update(self.air_table.collision_count)
                    if (-1000 < self.pk_collision_cnt.result < 10000):
                        self.pk_collision_cnt.draw( self.game_window.surface, 10, 40, width_px=45, fill=4)
                
                # Clean out old bullets.
                for thisPuck in self.air_table.pucks[:]:  # [:] indicates a copy 
                    if (thisPuck.bullet) and ((self.air_table.time_s - thisPuck.birth_time_s) > thisPuck.age_limit_s):
                        thisPuck.delete()

                self.env.remove_healthless_pucks()
                
                # Draw pucks, springs, mouse tethers, and jets.
                if (self.air_table.engine == "box2d"):
                    for eachWall in self.air_table.walls:
                        eachWall.draw()
                else:
                    self.air_table.draw()

                for eachpuck in self.air_table.pucks:
                    eachpuck.draw()
                    if (eachpuck.jet != None):
                        if eachpuck.jet.client.active:
                            eachpuck.gun.draw_shield()
                            eachpuck.jet.draw()
                            eachpuck.gun.draw()
                            
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
            
            # Jello madness game timer
            if self.air_table.jello_tangle_checking_enabled:
                if (self.air_table.engine == "box2d"): self.air_table.tangle_checker_time_s += self.air_table.dt_s
                if self.air_table.tangled:
                    self.air_table.game_time_s += self.air_table.dt_s

        return demo_index
