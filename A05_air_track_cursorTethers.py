#!/usr/bin/env python3

# Filename: A05_air_track_cursorTethers.py

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

class Client:
    def __init__(self, cursorString_color):
        self.cursor_location_px = (0,0)   # x_px, y_px
        self.mouse_button = 1             # 1, 2, or 3
        self.buttonIsStillDown = False        
        
        self.cursorString_color = cursorString_color
        
        self.selected_car = None
        
        # Define the nature of the cursor strings, one for each mouse button.
        self.mouse_strings = {'string1':{'c_drag':   2.0, 'k_Npm':   60.0},
                              'string2':{'c_drag':   0.2, 'k_Npm':    2.0},
                              'string3':{'c_drag':  20.0, 'k_Npm': 1000.0}}
                                        
    def calc_tether_forces_on_cars(self):
        # Calculated the string forces on the selected car and add to the aggregate
        # that is stored in the car object.
        
        # Only check for a selected car if one isn't already selected. This keeps
        # the car from unselecting if cursor is dragged off the car!
        if (self.selected_car == None):
            if self.buttonIsStillDown:
                self.selected_car = air_track.checkForCarAtThisPosition(self.cursor_location_px)        
        
        # If a car is selected
        else:
            if not self.buttonIsStillDown:
                # Unselect the car and bomb out of here.
                self.selected_car.selected = False
                self.selected_car = None
                return None
            
            # If button is down, calculate the forces on the car.
            else:
                # Use dx difference to calculate the hooks law force being applied by the tether line. 
                # If you release the mouse button after a drag it will fling the car.
                # This tether force will diminish as the car gets closer to the mouse point.
                dx_m = env.m_from_px( self.cursor_location_px[0]) - self.selected_car.center_m
                
                stringName = "string" + str(self.mouse_button)
                self.selected_car.cursorString_spring_force_N  += dx_m * self.mouse_strings[stringName]['k_Npm']
                self.selected_car.cursorString_carDrag_force_N += (self.selected_car.v_mps * 
                                                                   (-1) * self.mouse_strings[stringName]['c_drag'])
            
    def draw_cursor_string(self):
        car_center_xy_px = (env.px_from_m(self.selected_car.center_m), self.selected_car.center_y_px)        
        pygame.draw.line(game_window.surface, self.cursorString_color, car_center_xy_px, self.cursor_location_px, 1)

            
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
        
        # Use y midpoint for drawing the cursor line.
        self.center_y_px = int(round( float(game_window.height_px - self.height_px) + float(self.height_px)/2.0) )
        # For use with cursor-tethers selection.
        self.selected = False
        
        self.width_m = env.m_from_px( width_px)
        self.halfwidth_m = self.width_m/2.0
        
        self.height_m = env.m_from_px( height_px)
        
        # Initialize the position and velocity of the car. These are affected by the
        # physics calcs in the Track.
        self.center_m = env.m_from_px(left_px) + self.halfwidth_m
        self.v_mps = v_mps
        
        # Aggregate type forces acting on car.
        self.cursorString_spring_force_N = 0
        self.cursorString_carDrag_force_N = 0

        self.density_kgpm2 = 600.0
        self.m_kg = self.height_m * self.width_m * self.density_kgpm2
        
        # Increment the car count. This class variable is shared amoung all instances of the
        # car class.
        air_track.carCount += 1
        # Name this car based on this air_track attribute.
        self.name = air_track.carCount
        print("New car name =", self.name)
        
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
        
        self.collision_count = 0
        
        self.fix_wall_stickiness = True # False True
        self.fix_car_stickiness = True # False True
        
    def checkForCarAtThisPosition(self, cursor_location_xy):
        x_px = cursor_location_xy[0]
        y_px = cursor_location_xy[1]
        x_m = env.m_from_px(x_px)
        for car in self.cars:
            if (((x_m > car.center_m - car.halfwidth_m) and (x_m < car.center_m + car.halfwidth_m)) and
                (y_px > game_window.height_px - car.height_px)):
                car.selected = True
                return car
        return None
    
    def update_SpeedandPosition(self, car, dt_s):
        
        # Add up all the forces on the car.
        car_forces_N = (car.m_kg * self.g_mps2) + (car.cursorString_spring_force_N + 
                                                   car.cursorString_carDrag_force_N )
        
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
        
        # Reset the aggregate forces.
        car.cursorString_spring_force_N = 0
        car.cursorString_carDrag_force_N = 0
        
    def check_for_collisions(self):
        # Collisions with walls.
        # Enumerate so can efficiently check car-car collisions below.
        
        for i, car in enumerate(self.cars):
            
            # Collisions with Left and Right wall.
            #   If left-edge of the car is less than...                OR  If right-edge of car is greater than...
            if ((car.center_m - car.width_m/2.0) < game_window.left_m) or ((car.center_m + car.width_m/2.0) > game_window.right_m):
                self.collision_count += 1
                
                if self.fix_wall_stickiness:
                    self.correct_wall_penetrations(car)
            
                car.v_mps = -car.v_mps * self.coef_rest_wall                
            
            # This makes use of the "enumerate"d for loop above. 
            # In doing so, it avoids checking the self-self case and avoids checking pairs twice
            # like (2 with 3) and (3 with 2).
            # Example checks: (1 with 2,3,4,5), (2 with 3,4,5), (3 with 4,5), (4 with 5) etc...
            for ocar in self.cars[i+1:]:
                # Check for overlap with other rectangle.
                if (abs(car.center_m - ocar.center_m) < (car.halfwidth_m + ocar.halfwidth_m)):
                    self.collision_count += 1

                    if self.color_transfer == True:
                        (car.color, ocar.color) = (ocar.color, car.color)
                    
                    # Prevent sticking to other cars.
                    if self.fix_car_stickiness:
                        self.correct_car_penetrations(car, ocar)
                    
                    # Calculate the new post-collision velocities.
                    (car.v_mps, ocar.v_mps) = self.car_and_ocar_vel_AFTER_collision( car, ocar)

    def car_and_ocar_vel_AFTER_collision(self, car, ocar, CR=None):
        # If no override CR is provided, use the car's value.
        if (CR == None):
            CR = self.coef_rest_car
            
        # Calculate the AFTER velocities.
        car_vel_AFTER_mps =  ( (CR * ocar.m_kg * (ocar.v_mps - car.v_mps) + car.m_kg*car.v_mps + ocar.m_kg*ocar.v_mps)/
                               (car.m_kg + ocar.m_kg) )
        ocar_vel_AFTER_mps = ( (CR * car.m_kg *  (car.v_mps - ocar.v_mps) + car.m_kg*car.v_mps + ocar.m_kg*ocar.v_mps)/
                               (car.m_kg + ocar.m_kg) )

        return (car_vel_AFTER_mps, ocar_vel_AFTER_mps)
        
    def correct_wall_penetrations(self, car):
        penetration_left_x_m = game_window.left_m - (car.center_m - car.halfwidth_m)
        if penetration_left_x_m > 0:
            car.center_m += 2 * penetration_left_x_m
        
        penetration_right_x_m = (car.center_m + car.halfwidth_m) - game_window.right_m
        if penetration_right_x_m > 0:
            car.center_m -= 2 * penetration_right_x_m
    
    def correct_car_penetrations(self, car, ocar):
        relative_spd_mps = abs(car.v_mps - ocar.v_mps)
        penetration_m = (car.halfwidth_m + ocar.halfwidth_m) - abs(car.center_m - ocar.center_m)
        
        penetration_time_s = penetration_m / relative_spd_mps
        
        # First, back up the two cars, to their collision point, along their incoming trajectory paths.
        # Use BEFORE collision velocities here!
        car.center_m  -= car.v_mps  * penetration_time_s
        ocar.center_m -= ocar.v_mps * penetration_time_s
        
        # Calculate the velocities along the normal AFTER the collision. Use a CR (coefficient of restituion)
        # of 1 here to better avoid stickiness.
        (car_vel_AFTER_mps, ocar_vel_AFTER_mps) = self.car_and_ocar_vel_AFTER_collision( car, ocar, CR=1.0)

        # Finally, travel another penetration time worth of distance using these AFTER-collision velocities.
        # This will put the cars where they should have been at the time of collision detection.
        car.center_m  += car_vel_AFTER_mps  * penetration_time_s
        ocar.center_m += ocar_vel_AFTER_mps * penetration_time_s
    
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
        self.px_to_m = length_m/float(length_px)
        self.m_to_px = (float(length_px)/length_m)
        
        # Add a local (non-network) client to the client dictionary.
        self.clients = {'local':Client(THECOLORS["green"])}
    
    # Convert from meters to pixels
    def px_from_m(self, dx_m):
        return int(round(dx_m * self.m_to_px))
    
    # Convert from pixels to meters
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m
        
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
                elif (event.key==K_s):
                    air_track.fix_wall_stickiness = not air_track.fix_wall_stickiness
                    air_track.fix_car_stickiness = not air_track.fix_car_stickiness
                elif (event.key==K_c):
                    air_track.color_transfer = not air_track.color_transfer
                else:
                    return "Nothing set up for this key."
            
            elif (event.type == pygame.KEYUP):
                pass
            
            elif (event.type == pygame.MOUSEBUTTONDOWN):
                self.clients['local'].buttonIsStillDown = True
            
                (button1, button2, button3) = pygame.mouse.get_pressed()
                if button1:
                    self.clients['local'].mouse_button = 1
                elif button2:
                    self.clients['local'].mouse_button = 2
                elif button3:
                    self.clients['local'].mouse_button = 3
                else:
                    self.clients['local'].mouse_button = 0
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self.clients['local'].buttonIsStillDown = False
                self.clients['local'].mouse_button = 0
        
        if self.clients['local'].buttonIsStillDown:
            # If it down, get the cursor position.
            self.clients['local'].cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()
                
        
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
        dt_s = float(myclock.tick(framerate_limit) * 1e-3)
        
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
        
        # Calculate client related forces.
        for client_name in env.clients:
            env.clients[client_name].calc_tether_forces_on_cars()
        
        # Update velocity and x position of each car based on the dt_s for this frame.
        for car in air_track.cars:
            air_track.update_SpeedandPosition(car, dt_s)
        
        # Check for collisions and apply collision physics to determine resulting
        # velocities.
        air_track.check_for_collisions()
        #print("Collision count =", air_track.collision_count, air_track.fix_wall_stickiness, air_track.fix_car_stickiness)
        
        # Draw the car at the new position.
        for car in air_track.cars:
            car.draw_car()
            
        # Draw cursor strings.
        for client_name in env.clients:
            if (env.clients[client_name].selected_car != None):
                env.clients[client_name].draw_cursor_string()
                    
        # Update the total time since starting.
        time_s += dt_s
        
        # Make this update visible on the screen.
        pygame.display.flip()
            
#============================================================
# Run the main program.    
#============================================================

main()