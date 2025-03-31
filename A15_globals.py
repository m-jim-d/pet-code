#!/usr/bin/env python3

# Filename: A15_globals.py

"""
Shared global state for the simulation environment.

This module maintains global references to key simulation components that need to be
accessed across different parts of the application. While these globals are initially
set to None, they are guaranteed to be properly initialized before any code attempts
to use them, thanks to the initialization sequence in GameLoop:

1. When modules import this file, they get the None values
2. GameLoop.__init__() creates the actual objects (Environment, GameWindow, AirTable)
3. GameLoop.__init__() assigns these objects to the global variables
4. Only then does GameLoop.start() begin calling functions that use these globals

This pattern helps avoid circular imports while maintaining a clean way to share
these essential objects across the application. The globals are effectively read-only
after their initial setup by GameLoop.
"""

# Global variables shared across scripts
env = None
game_window = None
air_table = None