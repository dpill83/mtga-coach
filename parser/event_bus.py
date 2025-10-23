#!/usr/bin/env python3
"""
Event Bus / WebSocket Server

WebSocket server for broadcasting parsed MTGA events to connected clients.
Handles multiple connections and provides heartbeat mechanism.
"""

import asyncio
import json
import logging
import time
from typing import Set, Dict, Any, Optional
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from .events import GameEvent

logger = logging.getLogger(__name__)

class EventBus:
    """WebSocket-based event bus for MTGA events."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.server = None
        self.is_running = False
        self.heartbeat_interval = 30.0  # seconds
        self.last_heartbeat = time.time()
        
    async def register_client(self, websocket: WebSocketServerProtocol, path: str):
        """Register a new WebSocket client."""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}. Total clients: {len(self.clients)}")
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to MTGA Coach Event Bus",
                "server_info": {
                    "version": "1.0.0",
                    "heartbeat_interval": self.heartbeat_interval
                }
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Keep connection alive
            async for message in websocket:
                # Handle client messages (ping, etc.)
                try:
                    data = json.loads(message)
                    await self._handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {websocket.remote_address}: {message}")
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error in client connection: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client removed: {websocket.remote_address}. Total clients: {len(self.clients)}")
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle messages from clients."""
        message_type = data.get("type", "")
        
        if message_type == "ping":
            # Respond to ping with pong
            pong_msg = {
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(pong_msg))
            
        elif message_type == "subscribe":
            # Handle subscription requests
            event_types = data.get("event_types", [])
            logger.info(f"Client {websocket.remote_address} subscribed to: {event_types}")
            
        elif message_type == "unsubscribe":
            # Handle unsubscription requests
            logger.info(f"Client {websocket.remote_address} unsubscribed")
            
        else:
            logger.warning(f"Unknown message type from client: {message_type}")
    
    async def broadcast_event(self, event: GameEvent):
        """Broadcast a game event to all connected clients."""
        if not self.clients:
            logger.debug("No clients connected, skipping event broadcast")
            return
        
        try:
            # Convert event to JSON
            event_data = self._event_to_dict(event)
            message = json.dumps(event_data)
            
            # Send to all connected clients
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Error sending to client {client.remote_address}: {e}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.clients.discard(client)
                logger.info(f"Removed disconnected client: {client.remote_address}")
            
            logger.debug(f"Broadcasted event to {len(self.clients)} clients")
            
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")
    
    def _event_to_dict(self, event: GameEvent) -> Dict[str, Any]:
        """Convert a GameEvent to dictionary for JSON serialization."""
        try:
            # Use Pydantic's dict() method
            event_dict = event.dict()
            
            # Add server metadata
            event_dict["server_metadata"] = {
                "broadcast_time": datetime.now().isoformat(),
                "client_count": len(self.clients)
            }
            
            return event_dict
            
        except Exception as e:
            logger.error(f"Error converting event to dict: {e}")
            return {
                "type": "error",
                "message": f"Failed to serialize event: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_heartbeat(self):
        """Send heartbeat to all clients."""
        if not self.clients:
            return
        
        heartbeat_msg = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "server_time": time.time(),
            "client_count": len(self.clients)
        }
        
        message = json.dumps(heartbeat_msg)
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending heartbeat to client {client.remote_address}: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients.discard(client)
        
        self.last_heartbeat = time.time()
        logger.debug(f"Sent heartbeat to {len(self.clients)} clients")
    
    async def start_server(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self.register_client,
                self.host,
                self.port
            )
            self.is_running = True
            logger.info(f"Event bus server started on {self.host}:{self.port}")
            
            # Start heartbeat task
            asyncio.create_task(self._heartbeat_loop())
            
        except Exception as e:
            logger.error(f"Failed to start event bus server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server."""
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.is_running = False
                logger.info("Event bus server stopped")
                
        except Exception as e:
            logger.error(f"Error stopping event bus server: {e}")
    
    async def _heartbeat_loop(self):
        """Background task for sending heartbeats."""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.is_running:
                    await self.send_heartbeat()
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status information."""
        return {
            "is_running": self.is_running,
            "host": self.host,
            "port": self.port,
            "client_count": len(self.clients),
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_interval": self.heartbeat_interval
        }

class EventBusManager:
    """Manager for the event bus with queue processing."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.event_bus = EventBus(host, port)
        self.event_queue = asyncio.Queue()
        self.is_processing = False
        
    async def start(self):
        """Start the event bus and processing loop."""
        await self.event_bus.start_server()
        self.is_processing = True
        asyncio.create_task(self._process_events())
        logger.info("Event bus manager started")
    
    async def stop(self):
        """Stop the event bus and processing."""
        self.is_processing = False
        await self.event_bus.stop_server()
        logger.info("Event bus manager stopped")
    
    async def queue_event(self, event: GameEvent):
        """Queue an event for broadcasting."""
        await self.event_queue.put(event)
    
    async def _process_events(self):
        """Process queued events."""
        while self.is_processing:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Broadcast event
                await self.event_bus.broadcast_event(event)
                
            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")

async def test_event_bus():
    """Test function for the event bus."""
    from .events import GameStartEvent, EventType
    
    # Create event bus
    event_bus = EventBusManager()
    
    try:
        # Start server
        await event_bus.start()
        print("Event bus started")
        
        # Create test event
        test_event = GameStartEvent(
            event_type=EventType.GAME_START,
            player_life=20,
            opponent_life=20
        )
        
        # Queue and broadcast event
        await event_bus.queue_event(test_event)
        print("Test event queued")
        
        # Wait a bit
        await asyncio.sleep(2)
        
    finally:
        await event_bus.stop()
        print("Event bus stopped")

if __name__ == "__main__":
    asyncio.run(test_event_bus())
