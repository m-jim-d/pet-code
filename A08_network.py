#!/usr/bin/env python3

# Filename: A08_network.py

"""
Network Module for Multiplayer

This module provides real-time networking support for a multi-client application
where clients share mouse movements and keyboard states through a central server.
The server maintains client states and renders a shared view of all client activities.

Key Features:
- Low-latency mouse position tracking using TCP_NODELAY
- Support for up to 10 simultaneous clients
- Custom state update handlers for extended functionality
- Stable window-drag handling through socket draining
- FPS monitoring with smoothed display

Example Usage:
    Server side:
        clientStates = ClientData()  # Create state container
        server = GameServer(clientStates, host='0.0.0.0', port=5000)
        while True:
            server.accept_clients()  # Non-blocking client acceptance

    Client side:
        client = GameClient(host='server_ip', port=5000)
        client.connect()
        while running:
            client.send_state({'mouseXY': (x,y), 'mouseB1': 'U'/'D', ...})
"""

import socket
import pickle
import select
import threading
import time
import types
from pygame.color import THECOLORS

def setClientColors():
    """
    Create a color scheme for up to 10 clients.
    
    Colors are chosen to be visually distinct and work well for both
    cursor display and drawing history visualization.
    """
    client_colors = {
        'C1': THECOLORS["maroon1"],
        'C2': THECOLORS["tan"],
        'C3': THECOLORS["cyan"],
        'C4': THECOLORS["palegreen3"],
        'C5': THECOLORS["pink"],
        'C6': THECOLORS["gold"],
        'C7': THECOLORS["coral"],
        'C8': THECOLORS["palevioletred2"],
        'C9': THECOLORS["peachpuff"],
        'C10': THECOLORS["rosybrown3"]
    }
    return client_colors

class GameServer:
    """
    Central server managing multiple client connections and state updates.
    
    Handles client connections in separate threads, maintains client states,
    and supports custom state update handlers. Uses TCP_NODELAY for minimal
    mouse movement latency and includes special handling for window drag operations.
    """
    
    def __init__(self, host='localhost', port=5000, 
                       update_function=None, clientStates=None, signInOut_function=None):
        """
        Initialize the server with state management and optional custom behavior.
        
        Args:
            clientStates: Container holding all client state data
            host: Server IP address, use '0.0.0.0' for all interfaces
            port: Server port number
            update_function: custom function for updating client state
            clientStates: dictionary of Client objects on the server
        """
        # Setup primary server socket with minimal latency configuration
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        
        self.clients = {}  # Maps client sockets to (address, name) tuples
        self.client_counter = 0
        self.running = True
        print(f"Server started on {host}:{port}")
        
        # Setup custom update handlers
        if update_function:
            self.custom_update = types.MethodType(update_function, self)
            self.CS_data = clientStates
        else:
            self.custom_update = None
            self.CS_data = None
        
        if signInOut_function:
            self.signInOut_function = types.MethodType(signInOut_function, self)
        else:
            self.signInOut_function = None

        self.updateCount = 0
    
    def drain_socket(self, client_socket):
        """
        Clear accumulated data from a client socket during window drag pauses.
        
        Critical for maintaining connection stability during UI operations that
        might temporarily block the main thread.
        """
        while True:
            ready = select.select([client_socket], [], [], 0.0)[0]
            if not ready:
                break
            client_socket.recv(1024)  # Discard any queued data
    
    def handle_client(self, client_socket, client_address, client_name):
        """
        Process all communication with a connected client.
        
        Runs in a separate thread for each client, handling:
        - Initial setup and name assignment
        - Continuous state updates
        - Window drag detection and handling
        - Clean disconnection
        """
        print(f"New connection from {client_address} assigned name {client_name}")
        
        # Send client their assigned name
        try:
            connection_info = {'client_name': client_name}
            client_socket.send(pickle.dumps(connection_info))
            if (self.signInOut_function):
                self.signInOut_function(client_name, activate=True)

        except socket.error:
            self.remove_client(client_socket)
            return
        
        last_time = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                dt = current_time - last_time
                
                # Handle window drag pauses
                if dt > 0.1:  # 100ms threshold indicates a pause
                    print(f"pygame window paused: {dt:.2f} sec")
                    self.drain_socket(client_socket)
                    last_time = current_time
                    continue
                
                # Check for new client data with 2-second timeout
                ready = select.select([client_socket], [], [], 2.0)[0]
                
                if ready:
                    try:
                        data = client_socket.recv(1024)
                        if not data:  # Client disconnected
                            if (self.signInOut_function):
                                self.signInOut_function(client_name, activate=False)
                            break
                        
                        state_dict = pickle.loads(data)
                        # Use custom or default state update
                        if self.custom_update:
                            self.custom_update( client_name, state_dict)
                        
                    except socket.error:
                        break  # Socket error means client is gone
                    
                last_time = current_time
                
            except Exception as e:
                if "forcibly closed" not in str(e):
                    print(f"error in handle_client while: {str(e)}")
                continue
        
        self.remove_client(client_socket)

    def remove_client(self, client_socket):
        """
        Clean up client resources on disconnection.
        
        Handles socket closure, state cleanup, and client list maintenance.
        """
        if client_socket in self.clients:
            addr, client_name = self.clients[client_socket]
            if (self.signInOut_function):
                self.signInOut_function(client_name, activate=False)
            print(f"Client {client_name} ({addr}) disconnected")
            client_socket.close()
            del self.clients[client_socket]
                
    def accept_clients(self):
        """
        Accept new client connections without blocking.
        
        Creates a new thread for each connecting client to handle their
        communication independently.
        """
        ready = select.select([self.server_socket], [], [], 0.0)[0]
        if ready:  # Client waiting to connect
            try:
                client_socket, client_address = self.server_socket.accept()
                
                self.client_counter += 1
                client_name = f"C{self.client_counter}"
                self.clients[client_socket] = (client_address, client_name)
                
                # Create separate thread for this client's communication
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address, client_name)
                )
                client_thread.daemon = True  # Thread will close with main program
                client_thread.start()
            
            except socket.error:
                pass
    
    def stop(self):
        """Perform clean shutdown of the server."""
        self.running = False
        for client_socket in list(self.clients.keys()):
            self.remove_client(client_socket)
        self.server_socket.close()


class GameClient:
    """
    Client-side network handler for mouse/keyboard state transmission.
    
    Manages connection to server and continuous state updates. Uses TCP_NODELAY
    for minimal latency in mouse position transmission.
    """
    
    def __init__(self, host='localhost', port=5000):
        """
        Initialize client networking.
        
        Args:
            host: Server IP address
            port: Server port number
        """
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_address = (host, port)
        self.running = False
        self.client_name = "no-one" # default
        self.id = 0
        
    def connect(self):
        """
        Connect to server and receive assigned client identifier.
        
        Establishes connection and receives client name (e.g., 'C1')
        from server. Sets running state on successful connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client_socket.connect(self.server_address)
            
            # Wait briefly for server response
            ready = select.select([self.client_socket], [], [], 0.1)[0]
            if ready:
                data = self.client_socket.recv(1024)
                if data:
                    connection_info = pickle.loads(data)
                    self.client_name = connection_info['client_name']
                    print(f"Connected to server as {self.client_name}")
                    self.id = int(self.client_name.strip("C"))
                    self.running = True
                    return True
        
        except socket.error as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_state(self, state):
        """
        Serialize and send client's current input state to server
        
        Args:
            state: Dictionary containing current input state:
                  {'mouseXY': (x,y),
                   'mouseB1': 'U'/'D',
                   'w','a','s','d': 'U'/'D',
                   'ID': client_id}
        """
        try:
            pickled_state = pickle.dumps(state)
            self.client_socket.send(pickled_state)
        except socket.error:
            self.running = False


class RunningAvg:
    """
    Calculate and display smoothed framerate values.
    
    Maintains a rolling average over a fixed number of samples,
    rounding results to nearest multiple of base value for stable display.
    """
    
    def __init__(self, n_target, pygame_instance, colorScheme='dark'):
        """
        Initialize averaging system.
        
        Args:
            n_target: Number of samples to average
            pygame_instance: Reference to pygame for text rendering
            colorScheme: to provide contrast to main background.
        """
        self.n_target = n_target
        self.base = 5  # Round to nearest multiple of 5 for stable display
        self.reset()
        self.pygame = pygame_instance
        self.font = self.pygame.font.SysFont("Courier", 16) # Courier 16, Arial 19, Consolas ??
        
        if colorScheme == 'dark':
            self.backGroundColor = THECOLORS["black"]
            self.textColor = THECOLORS["white"]
        elif colorScheme == 'light':
            self.backGroundColor = THECOLORS["white"]
            self.textColor = THECOLORS["black"]
    
    def update(self, new_value):
        if self.n_target == 1:
            self.result = new_value
            return self.result
        
        """
        Add new value to running average.
        
        Maintains fixed window size by removing oldest value when full.
        Returns the smoothed and rounded result.
        """
        if self.n_in_avg < self.n_target:
            self.total += new_value
            self.n_in_avg += 1
        else:
            # Add new value and remove oldest
            self.total += new_value - self.values[0]
            self.values.pop(0)
        self.values.append(new_value)
        
        raw_result = self.total / self.n_in_avg
        
        # Round to nearest multiple of base
        self.result = self.base * round(raw_result/self.base)
    
    def reset(self):
        self.n_in_avg = 0
        self.result = 0.0
        self.values = []
        self.total = 0.0
    
    def draw(self, pygame_display, pos_x, pos_y, width_px=35, fill=3):
        """
        Display current average on pygame surface.
        
        Args:
            pygame_display: Surface to draw on
            pos_x, pos_y: Position to draw the value
        """
            
        # Draw background for text
        self.pygame.draw.rect(pygame_display, self.backGroundColor,
                            self.pygame.Rect(pos_x, pos_y, width_px, 20))
        # Draw the value
        fps_string = f"{self.result:{fill}.0f}"  # right justified, "fill" spaces, 0 decimals
        txt_surface = self.font.render(fps_string, True, self.textColor)
        pygame_display.blit(txt_surface, [pos_x+3, pos_y+1])  # use pos_x+3 for Courier 16
