#!/usr/bin/env python3

# Filename: A13_m_air_table_objects.py

import math
from typing import Optional

import pygame
from pygame.color import THECOLORS

# Import the vector class from a local module
from A09_vec2d import Vec2D
# Global variables shared across scripts
import A10_m_globals as g
from A10_m_air_table_objects import Puck, Spring
from A12_m_air_table_objects import Tube, Jet as BaseJet

class Jet(BaseJet):
    def __init__(self, puck, sf_abs=True):
        # Associate the jet with the puck (referenced in the Tube class).
        super().__init__(puck, sf_abs=sf_abs)
                         
        # Scaler magnitude of jet force.
        self.jet_force_N = 1.3 * self.puck.mass_kg * abs(g.air_table.gON_2d_mps2.y)

    def turn_jet_forces_onoff(self):
        if (self.client.key_w == "D"):
            # Force on puck is in the opposite direction of the jet tube.
            self.puck.jet_force_2d_N = self.direction_2d_m * (-1) * self.jet_force_N
        else:    
            self.puck.jet_force_2d_N = self.direction_2d_m * 0.0
