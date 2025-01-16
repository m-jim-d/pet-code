#!/usr/bin/env python3

# Filename: A03_air_track_g_wallCollisions.py

# Python
import sys, os
import pygame
import datetime

# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

#=====================================================================
# Classes
#=====================================================================
        
class GameWindow:
    def __init__(self, screen_tuple_px):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]

        # Create a reference to display's surface object. This object is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)
        
        # Define the physics-world boundaries of the window.
        self.left_m = 0.0
        self.right_m = env.m_from_px(self.width_px)
        
        # Paint screen black.
        self.erase_and_update()
        
    def update_caption(self, title):
        pygame.display.set_caption(title)
        self.caption = title
        
    def erase_and_update(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.flip()
        

class Detroit:
    def __init__(self, color=THECOLORS["white"], left_px=10, width_px=26, height_px=98, v_mps=1):
        
        self.color = color
        
        self.height_px = height_px        
        self.top_px    = game_window.height_px - self.height_px
        self.width_px  = width_px
        
        self.width_m = env.m_from_px( width_px)
        self.halfwidth_m = self.width_m/2.0
        
        self.height_m = env.m_from_px( height_px)
        
        # Initialize the position and velocity of the car. These are affected by the
        # physics calcs in the Track.
        self.center_m = env.m_from_px(left_px) + self.halfwidth_m
        self.v_mps = v_mps

        self.density_kgpm2 = 600.0
        self.m_kg = self.height_m * self.width_m * self.density_kgpm2
        
        # Increment the car count.
        air_track.carCount += 1
        # Name this car based on this air_track attribute.
        self.name = air_track.carCount
        
        # Create a rectangle object based on these dimensions
        # Left: distance from the left edge of the screen in px.
        # Top:  distance from the top  edge of the screen in px.
        self.rect = pygame.Rect(left_px, self.top_px, self.width_px, self.height_px)
        
    def draw_car(self):
        # Update the pixel position of the car's rectangle object to match the value
        # controlled by the physics calculations.
        self.rect.centerx = env.px_from_m( self.center_m)
        
        # Draw the main rectangle.
        pygame.draw.rect(game_window.surface, self.color, self.rect)
            
        
class AirTrack:
    def __init__(self):
        # Initialize the list of cars.
        self.cars = []
        self.carCount = 0
        
        # Coefficients of restitution.
        self.coef_rest_base = 0.90  # Useful for reseting things.
        self.coef_rest_car = self.coef_rest_base
        self.coef_rest_wall = self.coef_rest_base
        
        # Component of gravity along the length of the track.
        self.gbase_mps2 = 9.8/20.0 # one 20th of g.
        self.g_mps2 = self.gbase_mps2
        
        self.color_transfer = False

    def update_SpeedandPosition(self, car, dt_s):
        
        # Add up all the forces on the car.
        car_forces_N = (car.m_kg * self.g_mps2) + 0.0 + 0.0
        
        # Calculate the acceleration based on the forces and Newton's law.
        car_acc_mps2 = car_forces_N / car.m_kg
        
        # Calculate the velocity at the end of this time step.
        v_end_mps = car.v_mps + (car_acc_mps2 * dt_s)
        
        # Calculate the average velocity during this timestep.
        v_avg_mps = (car.v_mps + v_end_mps)/2.0
        
        # Use the average velocity to calculate the new position of the car.
        # Physics note: v_avg*t is equivalent to (v*t + (1/2)*acc*t^2)
        car.center_m = car.center_m + (v_avg_mps * dt_s)
        
        # Assign the final velocity to the car.
        car.v_mps = v_end_mps
        
        if False and (car.name == 1):
            print(f"dt = {dt_s:4.4f}, v_avg_mps = {v_avg_mps:4.1f}, car #1 m = {car.center_m:4.2f}")
    
    def check_for_collisions(self):
        # Collisions with walls.
        # Enumerate so can efficiently check car-car collisions below.
        
        fix_wall_stickiness = True # False True
        
        for car in self.cars:
            
            # Collisions with Left and Right wall.
            #   If left-edge of the car is less than...                OR  If right-edge of car is greater than...
            if ((car.center_m - car.width_m/2.0) < game_window.left_m) or ((car.center_m + car.width_m/2.0) > game_window.right_m):
                
                if fix_wall_stickiness:
                    self.correct_wall_penetrations(car)

                car.v_mps = -car.v_mps * self.coef_rest_wall   
            
    def correct_wall_penetrations(self, car):
        penetration_left_x_m = game_window.left_m - (car.center_m - car.halfwidth_m)
        if penetration_left_x_m > 0:
            car.center_m += 2 * penetration_left_x_m
        
        penetration_right_x_m = (car.center_m + car.halfwidth_m) - game_window.right_m
        if penetration_right_x_m > 0:
            car.center_m -= 2 * penetration_right_x_m
    
    def make_some_cars(self, nmode):
        # Update the caption at the top of the pygame window frame.
        game_window.update_caption("Air Track (basic): Demo #" + str(nmode)) 
        
        if (nmode == 1):
            air_track.g_mps2 = 0
            air_track.carCount = 0
            self.cars.append( Detroit(color=THECOLORS["red" ], left_px = 240, width_px=26, v_mps=  0.2))
            self.cars.append( Detroit(color=THECOLORS["blue"], left_px = 340, width_px=26, v_mps= -0.2))
        
        elif (nmode == 2):
            air_track.g_mps2 = air_track.gbase_mps2
            air_track.carCount = 0
            self.cars.append( Detroit(color=THECOLORS["yellow" ], left_px = 240, width_px=26, v_mps= -0.1))
            self.cars.append( Detroit(color=THECOLORS["green"],   left_px = 440, width_px=50, v_mps= -0.2))
        
        elif (nmode == 3):
            air_track.carCount = 0
            air_track.g_mps2 = 0
            self.cars.append( Detroit(color=THECOLORS["yellow" ], left_px = 240, width_px=26, v_mps= -0.1))
            self.cars.append( Detroit(color=THECOLORS["green"],   left_px = 440, width_px=50, v_mps= -0.2))
            

class Environment:
    def __init__(self, length_px, length_m):
        self.px_to_m = length_m/length_px
        self.m_to_px = length_px/length_m
    
    # Convert from meters to pixels
    def px_from_m(self, dx_m):
        return round(dx_m * self.m_to_px)
    
    # Convert from pixels to meters
    def m_from_px(self, dx_px):
        return dx_px * self.px_to_m
        
    def get_local_user_input(self):
        
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                return 'quit'
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    return 'quit'
                elif (event.key==K_1):            
                    return 1
                elif (event.key==K_2):                          
                    return 2
                elif (event.key==K_3):                          
                    return 3
                else:
                    return "Nothing set up for this key."
            
            elif (event.type == pygame.KEYUP):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONDOWN):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONUP):
                pass
                
#============================================================
# Main procedural functions.
#============================================================

def main():

    # A few globals.
    global env, game_window, air_track
    
    # Initiate pygame
    pygame.init()

    # Tuple to define window dimensions
    window_size_px = window_width_px, window_height_px = 950, 120

    # Instantiate an Environment object for converting back and forth from pixels and meters.
    # The also creates the local client.
    env = Environment(window_width_px, 1.5)

    # Instantiate the window.
    game_window = GameWindow(window_size_px)

    # Instantiate an air track (this adds an empty car list to the track).
    air_track = AirTrack()

    # Make some cars (run demo #1).
    air_track.make_some_cars(1)

    # Instantiate clock to help control the framerate.
    myclock = pygame.time.Clock()
        
    # Control the framerate.
    framerate_limit = 400

    time_s = 0.0
    user_done = False
    
    while not user_done:
        
        # Erase everything.
        game_window.surface.fill(THECOLORS["black"])

        # Get the delta t for one frame (this changes depending on system load).
        dt_s = myclock.tick(framerate_limit) * 1e-3
        
        # Check for user initiated stop or demo change.
        resetmode = env.get_local_user_input()
        if (resetmode in [0,1,2,3,4,5,6,7,8,9]):
            print("reset mode =", resetmode)
            
            # This should remove all references to the cars and effectively deletes them.
            air_track.cars = []
            
            # Now just black everything out and update the screen.
            game_window.erase_and_update()
            
            # Build new set of cars based on the reset mode.
            air_track.make_some_cars( resetmode)
        
        elif (resetmode == 'quit'):
            user_done = True
            
        elif (resetmode != None):
            print(resetmode)
        
        # Update velocity and x position of each car based on the dt_s for this frame.
        for car in air_track.cars:
            air_track.update_SpeedandPosition(car, dt_s)
        
        # Check for collisions and apply collision physics to determine resulting
        # velocities.
        air_track.check_for_collisions()
        
        # Draw the car at the new position.
        for car in air_track.cars:
            car.draw_car()
        
        # Update the total time since starting.
        time_s += dt_s
        
        # Make this update visible on the screen.
        pygame.display.flip()
            
#============================================================
# Run the main program.    
#============================================================

main()