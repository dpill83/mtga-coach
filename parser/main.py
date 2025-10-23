#!/usr/bin/env python3
"""
MTGA Coach - Main Parser Application

Main entry point that integrates all components:
- Scryfall data cache
- Log path detection
- File tailer
- Log parser
- Event bus (WebSocket server)
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.scryfall_downloader import ScryfallDownloader
from parser.log_path import MTGALogPath
from parser.log_parser import MTGALogParser
from parser.file_tailer import BufferedLogTailer
from parser.event_bus import EventBusManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mtga_coach.log')
    ]
)
logger = logging.getLogger(__name__)

class MTGACoach:
    """Main MTGA Coach application."""
    
    def __init__(self, config_file: str = "config.env"):
        self.config_file = config_file
        self.card_cache = None
        self.log_path_detector = None
        self.log_parser = None
        self.file_tailer = None
        self.event_bus = None
        self.is_running = False
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file."""
        try:
            from dotenv import load_dotenv
            load_dotenv(self.config_file)
            
            self.mtga_log_path = os.getenv("MTGA_LOG_PATH", "auto")
            self.websocket_port = int(os.getenv("WEBSOCKET_PORT", "8765"))
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            
            # Set log level
            logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))
            
            logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
            # Use defaults
            self.mtga_log_path = "auto"
            self.websocket_port = 8765
            self.log_level = "INFO"
    
    async def initialize(self) -> bool:
        """Initialize all components."""
        try:
            logger.info("Initializing MTGA Coach...")
            
            # 1. Initialize Scryfall data cache
            logger.info("Loading Scryfall card cache...")
            self.card_cache = ScryfallDownloader()
            cache_data = self.card_cache.load_cards_cache()
            
            if not cache_data:
                logger.warning("Scryfall cache not found. Run 'python data/scryfall_downloader.py' first.")
                logger.info("Creating sample cache for testing...")
                # For testing, we'll continue without cache
                self.card_cache = None
            else:
                logger.info(f"Loaded {cache_data['metadata']['total_cards']} cards from cache")
            
            # 2. Initialize log path detector
            logger.info("Detecting MTGA log path...")
            self.log_path_detector = MTGALogPath()
            
            # 3. Initialize log parser
            logger.info("Initializing log parser...")
            self.log_parser = MTGALogParser(card_cache=self.card_cache)
            
            # 4. Initialize event bus
            logger.info("Initializing event bus...")
            self.event_bus = EventBusManager(port=self.websocket_port)
            
            logger.info("Initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the MTGA Coach."""
        try:
            if not await self.initialize():
                return False
            
            # Start event bus
            await self.event_bus.start()
            logger.info(f"Event bus started on port {self.websocket_port}")
            
            # Detect log file path
            log_file_path = self.log_path_detector.detect_log_path(self.mtga_log_path)
            
            if not log_file_path:
                logger.error("No MTGA log file found. Please check your MTGA installation.")
                logger.info("You can specify a custom path in config.env: MTGA_LOG_PATH=/path/to/output_log.txt")
                return False
            
            # Validate log file
            if not self.log_path_detector.validate_log_file(log_file_path):
                logger.warning(f"Log file validation failed: {log_file_path}")
                logger.info("Continuing anyway...")
            
            # Create file tailer
            self.file_tailer = BufferedLogTailer(
                file_path=log_file_path,
                callback=self._process_log_lines,
                batch_size=5,
                flush_interval=0.5
            )
            
            # Start file tailer
            if not self.file_tailer.start():
                logger.error("Failed to start file tailer")
                return False
            
            self.is_running = True
            logger.info(f"MTGA Coach started successfully")
            logger.info(f"Tailing log file: {log_file_path}")
            logger.info(f"WebSocket server: ws://localhost:{self.websocket_port}")
            logger.info("Press Ctrl+C to stop")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MTGA Coach: {e}")
            return False
    
    def _process_log_lines(self, lines: list):
        """Process a batch of log lines."""
        try:
            for line in lines:
                # Parse the log line
                event = self.log_parser.parse_log_line(line)
                
                if event:
                    # Queue event for broadcasting
                    asyncio.create_task(self.event_bus.queue_event(event))
                    
                    # Log the event
                    logger.debug(f"Parsed event: {event.event_type} - {event.timestamp}")
                    
        except Exception as e:
            logger.error(f"Error processing log lines: {e}")
    
    async def stop(self):
        """Stop the MTGA Coach."""
        try:
            logger.info("Stopping MTGA Coach...")
            
            self.is_running = False
            
            # Stop file tailer
            if self.file_tailer:
                self.file_tailer.stop()
                logger.info("File tailer stopped")
            
            # Stop event bus
            if self.event_bus:
                await self.event_bus.stop()
                logger.info("Event bus stopped")
            
            logger.info("MTGA Coach stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MTGA Coach: {e}")

async def main():
    """Main function."""
    # Create coach instance
    coach = MTGACoach()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(coach.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the coach
        if not await coach.start():
            logger.error("Failed to start MTGA Coach")
            return 1
        
        # Keep running until stopped
        while coach.is_running:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await coach.stop()
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await coach.stop()
        return 1

def run_sample_test():
    """Run a test with sample log data."""
    import os
    
    print("MTGA Coach - Sample Test")
    print("=" * 30)
    
    # Create sample log if it doesn't exist
    from parser.log_path import MTGALogPath
    detector = MTGALogPath()
    if not detector.create_sample_log():
        print("Failed to create sample log")
        return
    
    # Test with sample log
    sample_path = detector.get_sample_log_path()
    print(f"Testing with sample log: {sample_path}")
    
    # Create parser
    parser = MTGALogParser()
    
    # Parse sample log
    events = []
    with open(sample_path, 'r') as f:
        for line in f:
            event = parser.parse_log_line(line)
            if event:
                events.append(event)
    
    print(f"Parsed {len(events)} events:")
    for event in events:
        print(f"  - {event.event_type}: {event.timestamp}")

if __name__ == "__main__":
    import os
    
    # Check if we should run sample test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_sample_test()
    else:
        # Run the main application
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
