#!/usr/bin/env python3

# Filename: A09b_2D_vector_sandbox.py

import sys, os
import pygame

# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

# Import the vector class from a local module (in this same directory)
from A09_vec2d import Vec2D

from A08_network import RunningAvg

#=====================================================================
# Classes
#=====================================================================

class Vectors_Add():
    def __init__(self, vectors_2d_m=None, theColor=THECOLORS["green"]):
        self.color = theColor
        self.selectable = False
        self.radius_m = 0.10
        self.radius_px = round(env.px_from_m( self.radius_m))
        
        if vectors_2d_m == None:
            self.vectors_2d_m = v_sb.vectors
        else:
            self.vectors_2d_m = vectors_2d_m
        
        self.total_2d_m = Vec2D(0,0)
        self.total_history_2d_m = []
        self.total_history_tuples_px = []
        
        self.needing_reset = False
        
    def update(self, mode="reset"):
        self.total_2d_m = Vec2D(0,0)
        for eachvector_2d_m in self.vectors_2d_m:
            if mode == "add":
                # Change the base vector to the running total.
                eachvector_2d_m.base_2d_m = self.total_2d_m
                self.total_2d_m += eachvector_2d_m
            else:
                eachvector_2d_m.base_2d_m = Vec2D(0,0)
        
        # Put the current total vector into a FIFO.
        if (v_sb.tail_time_s > v_sb.tail_timelimit_s) and v_sb.enable_tails:
            self.total_history_2d_m.append( self.total_2d_m)
            # Displace the oldest part of the FIFO; pop it off.
            if len(self.total_history_2d_m) > 700:
                self.total_history_2d_m.pop(0)
            v_sb.tail_time_s = 0

    def draw_circle_vector(self, vec_A_2d_m, vec_B_2d_m, color=None, small_circle=False):
            if color==None:
                color = self.color
            
            # Draw line segment
            line_points = [env.ConvertWorldToScreen(vec_A_2d_m), env.ConvertWorldToScreen(vec_B_2d_m)]
            #pygame.draw.aaline(game_window.surface, color, line_points[0], line_points[1], True)
            pygame.draw.aaline(game_window.surface, color, line_points[0], line_points[1])
            
            # Draw circle.
            self.radius_px = round(env.px_from_m( self.radius_m))
            if small_circle:
                radius_px = round(self.radius_px/2.0)
            else:    
                radius_px = self.radius_px
            if radius_px < 1:
                radius_px = 1
            pygame.draw.circle(game_window.surface, color, env.ConvertWorldToScreen(vec_B_2d_m), radius_px, 1)
    
    def draw(self):
        if v_sb.display_total:
            self.update("add")
            # Draw the total vector.
            Visual_Vec2D( self.total_2d_m, theColor=self.color).draw()
            self.needing_reset = True
            
            # Draw the total vector's history.
            if v_sb.enable_tails:
                if v_sb.lines_not_points:
                    if len(self.total_history_2d_m) >= 2:
                        self.total_history_tuples_px = []
                        for point_2d_m in self.total_history_2d_m:
                            self.total_history_tuples_px.append( env.ConvertWorldToScreen( point_2d_m))
                        #pygame.draw.lines(game_window.surface, self.color, False, self.total_history_tuples_px, 1)
                        #pygame.draw.aalines(game_window.surface, self.color, False, self.total_history_tuples_px, True)
                        pygame.draw.aalines(game_window.surface, self.color, False, self.total_history_tuples_px)
                else:
                    for point_2d_m in self.total_history_2d_m:
                        pygame.draw.circle(game_window.surface, self.color, env.ConvertWorldToScreen( point_2d_m), 1, 1)
                    
        else:
            if self.needing_reset:
                # Reset these so all are drawn from the origin.
                self.update("reset")
                self.needing_reset = False

            
class Visual_Vec2D( Vec2D):
    def __init__(self, x_m_or_Vec2D, y_m=None, theColor=THECOLORS["yellow"], rotation_rate_dps=0):
        
        if isinstance( x_m_or_Vec2D, Vec2D):
            x_m = x_m_or_Vec2D.x
            y_m = x_m_or_Vec2D.y
        else:
            x_m = x_m_or_Vec2D
            y_m = y_m
        
        Vec2D.__init__(self, x_m, y_m)
        
        self.rotation_rate_dps = rotation_rate_dps
        
        self.radius_m = 0.10
        self.color = theColor
        self.selectable = True
        self.selected = False
        
        # Projection target
        self.projection_target_2d_m = None
        
        # Base vector (to displace the drawing of the vector from the origin)
        self.base_2d_m = Vec2D(0.0,0.0)
        
        # Arrowhead definition.
        self.sf_x = 0.3
        self.sf_y = 0.1
        self.arrowhead_vertices_2d_m =[Vec2D( -1.00 * self.sf_x, -0.50 * self.sf_y), 
                                       Vec2D( -1.00 * self.sf_x,  0.50 * self.sf_y), 
                                       Vec2D(  0.00 * self.sf_x,  0.00 * self.sf_y)]
        
        self.rt_vertices_2d_px  = []
        self.update()
        
    def update(self):
        # Rotate this vector a wee bit during each time step.
        if (not env.freeze) and (not self.selected):
            self.rotated(self.rotation_rate_dps * env.dt_s, sameVector=True)
        
        self.angle_deg = self.get_angle()
        
        # Rotate and translate the arrow head and convert for screen display.
        self.rotate_and_translate_vertices( self.arrowhead_vertices_2d_m, self.angle_deg)
        
    def rotate_and_translate_vertices(self, vertices_2d_m, angle_deg):
        # Put modified vectors in a new list.
        self.rt_vertices_2d_px = []
        for vertex_2d_m in vertices_2d_m:
            # Rotated and translated (add to the shaft).
            rt_vertex_2d_m = vertex_2d_m.rotated( angle_deg) + self + self.base_2d_m
            
            # Convert for screen display.
            rt_vertex_2d_px = env.ConvertWorldToScreen( rt_vertex_2d_m)
            
            self.rt_vertices_2d_px.append( rt_vertex_2d_px)
    
    def draw_selection_circle(self):
        # Draw circle.
        radius_px = round(env.px_from_m( self.radius_m))
        if radius_px < 1:
            radius_px = 1
        
        pygame.draw.circle(game_window.surface, self.color, env.ConvertWorldToScreen(self), radius_px, 1)
        
    def draw_vector(self):
        # Draw main body of the arrow: line from base point to end point.
        line_points = [env.ConvertWorldToScreen(self.base_2d_m), env.ConvertWorldToScreen(self + self.base_2d_m)]
        #pygame.draw.line(game_window.surface, self.color, line_points[0], line_points[1], 2)
        #pygame.draw.aaline(game_window.surface, self.color, line_points[0], line_points[1], True)
        pygame.draw.aaline(game_window.surface, self.color, line_points[0], line_points[1])
        
        # Draw the arrowhead
        if self.length_squared() > 0:
            if self.base_2d_m.equal(Vec2D(0.0,0.0)):
                arrow_head_line_thickness = 0
            else:
                arrow_head_line_thickness = 1
            pygame.draw.polygon(game_window.surface, self.color, self.rt_vertices_2d_px, arrow_head_line_thickness)
        
        # Draw a selection circle if there is a non-zero base vector.
        if self.base_2d_m.not_equal( Vec2D(0,0)):
            self.draw_selection_circle()          
    
    def draw(self):
        self.update()
        # Main vector
        self.draw_vector()
        
        if (self.selected and v_sb.enable_components):
            # Its two components
            Visual_Vec2D( self.x,      0, self.color).draw_vector()
            Visual_Vec2D(      0, self.y, self.color).draw_vector()
            # The normal
            if self.length_squared() > 0:
                normal_2d_m = self.normal()  # This returns a Vec2D object.
                Visual_Vec2D( normal_2d_m, theColor=THECOLORS["red"]).draw_vector()
                Visual_Vec2D( normal_2d_m.rotate90(), theColor=THECOLORS["red"]).draw_vector()
                
            Visual_Vec2D( self.projection_onto( self.projection_target_2d_m), theColor=self.color).draw_vector()
        
class VectorSandbox:
    def __init__(self, walls_dic):
        self.vectors = []
        self.walls = walls_dic
        self.selected_vector = None
        self.total_vector_2d_m = None
        
        self.display_total = False
        self.enable_components = True
        self.enable_tails = False
        self.lines_not_points = False
        
        self.tail_time_s = 0
        self.tail_timelimit_s = 1/30.0
        
    def draw(self):
        #{"L_m":0.0, "R_m":10.0, "B_m":0.0, "T_m":10.0}
        # Define endpoints for each axis.
        x_pos_2d_px =  env.ConvertWorldToScreen( Vec2D(  self.walls['R_m'],  0.0              ))
        x_neg_2d_px =  env.ConvertWorldToScreen( Vec2D( -self.walls['R_m'],  0.0              ))
        y_pos_2d_px =  env.ConvertWorldToScreen( Vec2D(                0.0,  self.walls['T_m']))
        y_neg_2d_px =  env.ConvertWorldToScreen( Vec2D(                0.0, -self.walls['T_m']))
        
        # Draw the two axes.
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], x_pos_2d_px,  x_neg_2d_px, 1)
        pygame.draw.line(game_window.surface, THECOLORS["orangered1"], y_pos_2d_px,  y_neg_2d_px, 1)
    
    def checkForVectorAtCursorPosition(self, x_px_or_tuple, y_px = None):
        if y_px == None:
            x_px = x_px_or_tuple[0]
            y_px = x_px_or_tuple[1]
        else:
            x_px = x_px_or_tuple
            y_px = y_px
        
        test_position_2d_m = env.ConvertScreenToWorld(Vec2D(x_px, y_px))
        for vector in self.vectors:
            if vector.selectable:
                vector_difference_2d_m = test_position_2d_m - vector
                # Use squared lengths for speed (avoid square root)
                mag_of_difference_m2 = vector_difference_2d_m.length_squared()
                if mag_of_difference_m2 < vector.radius_m**2:
                    vector.selected = True
                    return vector
        return None
        
    def updateSelectedVector(self):
        if (self.selected_vector == None):
            if env.buttonIsStillDown:
                self.selected_vector = self.checkForVectorAtCursorPosition(env.cursor_location_px)        
        else:
            if not env.buttonIsStillDown:
                # Deselect the vector and bomb out of here.
                self.selected_vector.selected = False
                self.selected_vector = None
                return None
            else:
                # Drag the vector to follow the cursor.
                cursor_pos_2d_m = env.ConvertScreenToWorld(Vec2D(env.cursor_location_px))
                self.selected_vector.x, self.selected_vector.y = cursor_pos_2d_m.x, cursor_pos_2d_m.y

                
class Environment:
    def __init__(self, screenSize_px, length_x_m):
        self.screenSize_px = Vec2D(screenSize_px)
        self.viewOffset_px = Vec2D(-self.screenSize_px.x/2,-self.screenSize_px.y/2)
        self.viewZoom = 1
        self.viewZoom_rate = 0.01
    
        self.key_b = 'U'
        self.key_n = 'U'
        self.key_m = 'U'
        self.key_h = 'U'
    
        self.px_to_m = length_x_m/float(self.screenSize_px.x)
        self.m_to_px = (float(self.screenSize_px.x)/length_x_m)
        
        self.inhibit_screen_clears = False
        
        # Keyboard/mouse state
        
        self.cursor_location_px = (0,0)   # x_px, y_px
        self.mouse_button = 1             # 1, 2, or 3
        self.buttonIsStillDown = False        
                
        self.selected_vector = None
        
        self.dt_s = 0
        self.freeze = False

        self.fr_avg = RunningAvg(500, pygame, colorScheme='light')
    
    # Convert from meters to pixels 
    def px_from_m(self, dx_m):
        return dx_m * self.m_to_px * self.viewZoom
    
    # Convert from pixels to meters
    # Note: still floating values here
    def m_from_px(self, dx_px):
        return float(dx_px) * self.px_to_m / self.viewZoom
    
    def control_zoom_and_view(self):
        if self.key_h == "D":
            self.viewZoom += self.viewZoom_rate * self.viewZoom
        if self.key_n == "D":
            self.viewZoom -= self.viewZoom_rate * self.viewZoom
    
    def ConvertScreenToWorld(self, point_2d_px):
        x_m = (                       point_2d_px.x + self.viewOffset_px.x) / (self.m_to_px * self.viewZoom)
        y_m = (self.screenSize_px.y - point_2d_px.y + self.viewOffset_px.y) / (self.m_to_px * self.viewZoom)
        return Vec2D( x_m, y_m)

    def ConvertWorldToScreen(self, point_2d_m):
        """
        Convert from world to screen coordinates (pixels).
        In the class instance, we store a zoom factor, an offset indicating where
        the view extents start at, and the screen size (in pixels).
        """
        x_px = (point_2d_m.x * self.m_to_px * self.viewZoom) - self.viewOffset_px.x
        y_px = (point_2d_m.y * self.m_to_px * self.viewZoom) - self.viewOffset_px.y
        y_px = self.screenSize_px.y - y_px

        # Return a tuple of integers.
        return Vec2D(x_px, y_px, "int").tuple()

    def get_user_input(self):
        # Get all the events since the last call to get().
        for event in pygame.event.get():
            if (event.type == pygame.QUIT): 
                sys.exit()
            elif (event.type == pygame.KEYDOWN):
                if (event.key == K_ESCAPE):
                    sys.exit()
                elif (event.key==K_KP1):
                    return "1p"
                elif (event.key==K_KP2):
                    return "2p"
                elif (event.key==K_KP3):
                    return "3p"
                elif (event.key==K_1):
                    return 1
                elif (event.key==K_2):
                    return 2
                elif (event.key==K_3):
                    return 3
                elif (event.key==K_4):
                    return 4
                elif (event.key==K_5):
                    return 5
                elif (event.key==K_6):
                    return 6
                elif (event.key==K_7):
                    return 7
                elif (event.key==K_8):
                    return 8
                elif (event.key==K_9):
                    return 9
                elif (event.key==K_0):
                    return 0
                
                # Sandbox control toggles.
                elif (event.key==K_c):
                    v_sb.enable_components = not v_sb.enable_components
                elif (event.key==K_t):
                    v_sb.enable_tails = not v_sb.enable_tails
                elif (event.key==K_f):
                    env.freeze = not env.freeze
                elif (event.key==K_a):
                    v_sb.display_total = not v_sb.display_total
                elif (event.key==K_l):
                    v_sb.lines_not_points = not v_sb.lines_not_points
                
                # Zoom keys.
                elif (event.key==K_b):
                    self.key_b = 'D'
                elif (event.key==K_n):
                    self.key_n = 'D'
                elif (event.key==K_m):
                    self.key_m = 'D'
                elif (event.key==K_h):
                    self.key_h = 'D'
                elif (event.key==K_q):
                    env.viewZoom = 1.00
                else:
                    return "nothing set up for this key"
            
            elif (event.type == pygame.KEYUP):
                    
                # Zoom keys
                if (event.key==K_b):
                    self.key_b = 'U'
                elif (event.key==K_n):
                    self.key_n = 'U'
                elif (event.key==K_m):
                    self.key_m = 'U'
                elif (event.key==K_h):
                    self.key_h = 'U'
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.buttonIsStillDown = True
            
                (button1, button2, button3) = pygame.mouse.get_pressed()
                if button1:
                    self.mouse_button = 1
                elif button2:
                    self.mouse_button = 2
                elif button3:
                    self.mouse_button = 3
                else:
                    self.mouse_button = 0
            
            elif event.type == pygame.MOUSEBUTTONUP:
                self.buttonIsStillDown = False
                self.mouse_button = 0
            
        if self.buttonIsStillDown:
            self.cursor_location_px = (mouseX, mouseY) = pygame.mouse.get_pos()

        
class GameWindow:
    def __init__(self, screen_tuple_px, title):
        self.width_px = screen_tuple_px[0]
        self.height_px = screen_tuple_px[1]
        
        # The initial World position vector of the Upper Right corner of the screen.
        # Yes, that's right y_px = 0 for UR.
        self.UR_2d_m = env.ConvertScreenToWorld(Vec2D(self.width_px, 0))
        
        # Create a reference to the display surface object. This is a pygame "surface".
        # Screen dimensions in pixels (tuple)
        self.surface = pygame.display.set_mode(screen_tuple_px)

        self.update_caption(title)
        
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()
        
    def update_caption(self, title):
        pygame.display.set_caption( title)
        self.caption = title
    
    def update(self):
        pygame.display.update()
        
    def clear(self):
        # Useful for shifting between the various demos.
        self.surface.fill(THECOLORS["black"])
        pygame.display.update()

#===========================================================
# Functions
#===========================================================

def make_some_vectors(resetmode):
    game_window.update_caption("Vector Sandbox V.1: Demo #" + str(resetmode)) 
    env.inhibit_screen_clears = False
    
    env.always_render = False
    
    if resetmode == 1:
        v_1 = Visual_Vec2D( 0.0,  4.0, THECOLORS["white"],  rotation_rate_dps=-20)
        v_sb.vectors.append( v_1)
        
        v_2 = Visual_Vec2D( 0.0,  1.0, THECOLORS["yellow"], rotation_rate_dps=180)
        v_sb.vectors.append( v_2)
        
        v_1.projection_target_2d_m = v_2
        v_2.projection_target_2d_m = v_1
    
        v_sb.total_vector_2d_m = Vectors_Add()
    
    elif resetmode == 2:
        v_1 = Visual_Vec2D( 0.0,  3.0, THECOLORS["white"],  rotation_rate_dps=-20)
        v_sb.vectors.append( v_1)
        
        v_2 = Visual_Vec2D( 0.0,  2.0, THECOLORS["yellow"], rotation_rate_dps=-40)
        v_sb.vectors.append( v_2)
        
        v_1.projection_target_2d_m = v_2
        v_2.projection_target_2d_m = v_1
    
        v_3 = Visual_Vec2D( 0.0,  1.0, THECOLORS["tan"],   rotation_rate_dps=-60)
        v_sb.vectors.append( v_3)
        v_3.projection_target_2d_m = v_1
        
        v_sb.total_vector_2d_m = Vectors_Add()
    
    elif resetmode == 3:    
        for j in range(1,11):
            temp = Visual_Vec2D( 0.0, 3, THECOLORS["white"],  rotation_rate_dps=-(10*j))
            v_sb.vectors.append( temp)
            v_sb.vectors[j-1].projection_target_2d_m = v_sb.vectors[0]
            
        v_sb.total_vector_2d_m = Vectors_Add()
        
    elif resetmode == 4:
        for j in range(1,11):
            temp = Visual_Vec2D( 0.0, 0.4*j, THECOLORS["white"],  rotation_rate_dps=-(10*j))
            v_sb.vectors.append( temp)
            v_sb.vectors[j-1].projection_target_2d_m = v_sb.vectors[0]
            
        v_sb.total_vector_2d_m = Vectors_Add()
        
    elif resetmode == 5:
        for j in range(1,11):
            temp = Visual_Vec2D( 0.0, 3-0.2*j, THECOLORS["white"],  rotation_rate_dps=-(10*j))
            v_sb.vectors.append( temp)
            v_sb.vectors[j-1].projection_target_2d_m = v_sb.vectors[0]
            
        v_sb.total_vector_2d_m = Vectors_Add()

    elif resetmode == 6:
        for j in range(1,41):
            temp = Visual_Vec2D( 0.0, 0.4*j, THECOLORS["white"],  rotation_rate_dps=-(10*j))
            v_sb.vectors.append( temp)
            v_sb.vectors[j-1].projection_target_2d_m = v_sb.vectors[0]
            
        v_sb.total_vector_2d_m = Vectors_Add()
        
    elif resetmode == 7:
        for j in range(1,141):
            temp = Visual_Vec2D( 0.0, 0.4*j, THECOLORS["white"],  rotation_rate_dps=-(10*j))
            v_sb.vectors.append( temp)
            v_sb.vectors[j-1].projection_target_2d_m = v_sb.vectors[0]
            
        v_sb.total_vector_2d_m = Vectors_Add()
        
    else:
        print("Nothing set up for this key.")
    
#============================================================
# Main procedural script.
#============================================================

def main():

    # A few globals.
    global env, game_window, v_sb
    
    pygame.init()

    myclock = pygame.time.Clock()

    window_dimensions_px = (800, 700)   #window_width_px, window_height_px

    # Create the first user/client and the methods for moving between the screen and the world.
    env = Environment(window_dimensions_px, 10.0) # 10m in along the x axis.

    game_window = GameWindow(window_dimensions_px, 'Vector Sandbox V.1')

    # Define the Left, Right, Bottom, and Top boundaries of the game window.
    v_sb = VectorSandbox({"L_m":0.0, "R_m":game_window.UR_2d_m.x, "B_m":0.0, "T_m":game_window.UR_2d_m.y})

    # Add some vectors to the table.
    demo_mode = 1
    make_some_vectors( demo_mode)

    # Font object for rendering text onto display surface.
    fnt_FPS = pygame.font.SysFont("Arial", 14)
    fnt_gameTimer = pygame.font.SysFont("Arial", 60)
    
    # Limit the framerate, but let it float below this limit.
    framerate_limit = 480.0   # 480

    while True:
        env.dt_s = float(myclock.tick( framerate_limit) * 1e-3)
        
        # Listen to the user: establish the state of the keyboard and mouse and determine if a new demo is called for.
        resetmode = env.get_user_input()
            
        # Reset the game based on local user control.
        if resetmode in ["1p","2p","3p",1,2,3,4,5,6,7,8,9,0]:
            demo_mode = resetmode
            print(resetmode)
            # Delete all the objects in the sandbox. Cleaning out these list reference to these objects effectively
            # deletes the objects.
            v_sb.total_vector_2d_m = None
            v_sb.vectors = []
            
            # Now just black out the screen.
            game_window.clear()
            
            # Reinitialize the demo.
            make_some_vectors( demo_mode)
                    
        # Control vector selection and mouse related movement.
        v_sb.updateSelectedVector()
            
        # Control the zoom
        env.control_zoom_and_view()
        
        # Erase the blackboard.
        if not env.inhibit_screen_clears:
            game_window.surface.fill((0,0,0))

        # Display FPS text.
        env.fr_avg.update( myclock.get_fps())
        env.fr_avg.draw( game_window.surface, 10, 10)

        # Draw axis for the vector sandbox.
        v_sb.draw()
        
        # Update and draw vectors (updates are in the draw methods)
        # Do the total first; so it's on the bottom.
        if v_sb.total_vector_2d_m != None:
            v_sb.total_vector_2d_m.draw()    
        # Then do the individual vectors.
        for eachvector in v_sb.vectors: 
            eachvector.draw()
        
        pygame.display.flip()

        v_sb.tail_time_s += env.dt_s
        
#============================================================
# Run the main program.    
#============================================================
        
main()