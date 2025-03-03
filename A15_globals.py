#!/usr/bin/env python3

# Filename: A15_globals.py

"""
Shared global state for the simulation environment.

This module maintains global references to key simulation components that need to be
accessed across different parts of the application.

Global Variables:
    env: The simulation environment instance
    game_window: The main game display window
    air_table: The simulation table/arena
"""

# Global variables shared across scripts
env = None
game_window = None
air_table = None
make_some_pucks = None