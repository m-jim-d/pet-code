## Physics Engine Tutorial (PET):

Please refer to the installation instructions provided on the PET website:

https://pet.triquence.org/

The codebase consists of both executable Python scripts and supporting module files.

This progression, originally a series of assignments, shows how the codebase evolves from simple PyGame demonstrations and 1D physics (air track) to 2D physics (air table) and multiplayer games. The A15 modules form a reusable framework that supports multiple physics implementations, from basic circular collisions to Box2D integration.

### Basic Framework and Concepts (A01-A07)
- `A01_game_loop_and_events.py`: Introduces basic PyGame game loop and event handling
- `A02a_string_rendering.py`: The one-page physics engine.
- `A02b_string_rendering_long.py`: A longer version of the one-pager.
- `A02c_air_track_framework.py`: Basic framework for air track (1D) physics simulation
- `A03_air_track_g_wallCollisions.py`: Adds gravity and wall collision detection
- `A04_air_track_carCollisions.py`: Implements collision detection between cars/objects
- `A05_air_track_cursorTethers.py`: Adds ability to tether objects to cursor
- `A06_air_track_gui_controls.py`: Implements GUI controls for simulation parameters
- `A07_air_track_hollow_cars.py`: Adds hollow car objects with internal physics

### Networking and Client-Server Architecture (A08)
Core Module:
- `A08_network.py`: Core networking functionality for multiplayer support

Executable Scripts:
- `A08_multiplayer_demo_client.py`: Demo client for multiplayer
- `A08_multiplayer_demo_server.py`: Demo server for multiplayer

### Vector Mathematics (A09)
Core Module:
- `A09_vec2d.py`: 2D vector class

Executable Scripts:
- `A09_2D_vector_class_testing.py`: Test suite for vector class
- `A09b_2D_vector_sandbox.py`: Sandbox for experimenting with vector operations

### 2D Physics Development and the Client (A10)
- `A10_2D_baseline_client.py`: Basic 2D physics client (use this client for all the following servers)
- `A10_2D_baseline_server.py`: Basic 2D physics server

### Game Development (A10_m-A14_m)
Modular Game Features:
- A10 Baseline:
  - `A10_m_globals.py`: Global constants and settings
  - `A10_m_game_loop.py`: Main game loop implementation
  - `A10_m_environment.py`: Game environment management
  - `A10_m_air_table.py`: Air table physics core
  - `A10_m_air_table_objects.py`: Basic game objects
  - `A10_m_server_baseline.py`: Server implementation

- A11 Rotating Tubes:
  - `A11_m_air_table_objects.py`: Rotating tube mechanics
  - `A11_m_server_rawtubes.py`: Server-side tube handling

- A12 Jet Propulsion:
  - `A12_m_air_table_objects.py`: Jet propulsion objects
  - `A12_m_server_jet.py`: Server-side jet physics

- A13 Enhanced Forces:
  - `A13_m_air_table_objects.py`: Advanced force calculations
  - `A13_m_server_jet_forces.py`: Server-side force handling

- A14 Combat System:
  - `A14_m_air_table_objects.py`: Projectile and weapon objects
  - `A14_m_server_gun.py`: Server-side combat mechanics

### Advanced Physics and Final Game Features (A15-A16)
Core Modules:
- `A15_air_table.py`: Core air table physics implementation with multiple collision engines
- `A15_air_table_objects.py`: Object definitions (pucks, walls, springs, jets, guns)
- `A15_game_loop.py`: manage the game loop and updates to the state of the air table
- `A15_environment.py`: Environment management, coordinate systems, and user interaction
- `A15_globals.py`: Global variables and shared state management
- `A15_pool_shots.py`: Pool game shot mechanics and trajectory calculations

Game Implementations:
- `A15a_2D_finished_game.py`: Complete 2D games, Puck Popper and Jello Madness

The Perfect-Kiss modification:
- `A15c_2D_perfect_kiss_serverN.py`: Perfect-collision physics for elastic pucks

Box2D Integration:
- `A16a_BodyTypes.py`: Box2D framework demo (must be run in pybox2d_framework_P3 subdirectory)
- `A16b_simple_airtrack_forces.py`: Simple force calculations using Box2D (without the pybox2d framework)
- `A16c_2D_B2D_serverN.py`: Full Box2D-based physics implementation of the games.