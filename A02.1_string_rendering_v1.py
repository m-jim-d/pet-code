#!/usr/bin/env python3

# Filename: A02.1_string_rendering_v1.py

import time

def render_airtrack(x_px, x_left_edge_px, x_right_edge_px):
    string = ''
    display_width_px = 126 # 126/7 = 18 meters
    for j in range(0, display_width_px):
        if (j == x_px):
            string += '*'
        elif (j==x_left_edge_px) or (j==x_right_edge_px):
            string += '|'
        else:
            string += ' '
    return string

def m_to_px(x_m):
    return round(x_m * 7.0)   # pixels per meter.
    
def x_fix_sticky( x_m, x_left_edge_m, x_right_edge_m):
    # Simple stickiness correction. Move it back to the surface.
    if (x_m < x_left_edge_m): 
        x_corrected_m = x_left_edge_m  
    elif (x_m > x_right_edge_m): 
        x_corrected_m = x_right_edge_m  
    return x_corrected_m
        
def main(): 
    x_left_edge_m   =  0.5
    x_right_edge_m  = 17.5
    
    dt_s   =  0.015
    x_m    = 11.0
    v_mps  = 17.0
    a_mps2 = -2.0
    
    try:
        while True:  # Run until Ctrl+C
            # Update the velocity and position.
            v_mps +=  a_mps2 * dt_s
            x_m   +=  v_mps  * dt_s
            
            # Check for wall collisions.
            if (x_m < x_left_edge_m) or (x_m > x_right_edge_m): 
                v_mps *= -1 * 0.80  # loss of 20% on each bounce.
                x_m = x_fix_sticky( x_m, x_left_edge_m, x_right_edge_m)
                
            display_string = render_airtrack( m_to_px( x_m), m_to_px( x_left_edge_m), m_to_px( x_right_edge_m))
            print(f"{display_string}x = {x_m:4.1f}   v = {v_mps:5.1f}")
            
            time.sleep(dt_s)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped by user (Ctrl+C)")

main()