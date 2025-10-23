#!/usr/bin/env python3
"""
MTGA Coach - Main Application with Heuristic Engine

Enhanced main application that includes the heuristic evaluation engine.
This is the complete version with AI decision-making capabilities.
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
from state.state_integration import StateIntegrationManager
from engine.heuristic_engine import HeuristicEngine

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

class MTGACoachWithHeuristic:
    """Complete MTGA Coach application with heuristic AI."""
    
    def __init__(self, config_file: str = "config.env"):
        self.config_file = config_file
        self.card_cache = None
        self.log_path_detector = None
        self.log_parser = None
        self.file_tailer = None
        self.state_integration = None
        self.heuristic_engine = None
        self.is_running = False
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load configuration from file."""
        try:
            import os
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
            logger.info("Initializing MTGA Coach with Heuristic AI...")
            
            # 1. Initialize Scryfall data cache
            logger.info("Loading Scryfall card cache...")
            self.card_cache = ScryfallDownloader()
            cache_data = self.card_cache.load_cards_cache()
            
            if not cache_data:
                logger.warning("Scryfall cache not found. Run 'python data/scryfall_downloader.py' first.")
                logger.info("Continuing without card cache...")
                self.card_cache = None
            else:
                logger.info(f"Loaded {cache_data['metadata']['total_cards']} cards from cache")
            
            # 2. Initialize log path detector
            logger.info("Detecting MTGA log path...")
            self.log_path_detector = MTGALogPath()
            
            # 3. Initialize log parser
            logger.info("Initializing log parser...")
            self.log_parser = MTGALogParser(card_cache=self.card_cache)
            
            # 4. Initialize state integration
            logger.info("Initializing state integration...")
            self.state_integration = StateIntegrationManager(port=self.websocket_port)
            
            # 5. Initialize heuristic engine
            logger.info("Initializing heuristic engine...")
            self.heuristic_engine = HeuristicEngine(self.state_integration.get_current_state())
            
            logger.info("Initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the MTGA Coach with heuristic AI."""
        try:
            if not await self.initialize():
                return False
            
            # Start state integration
            if not await self.state_integration.start():
                logger.error("Failed to start state integration")
                return False
            
            logger.info(f"State integration started on port {self.websocket_port}")
            
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
            logger.info(f"MTGA Coach with Heuristic AI started successfully")
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
                    # Process event through state integration
                    asyncio.create_task(self.state_integration.process_event(event))
                    
                    # Generate AI recommendations if it's our turn
                    if self._should_generate_recommendations(event):
                        asyncio.create_task(self._generate_ai_recommendations())
                    
                    # Log the event
                    logger.debug(f"Parsed event: {event.event_type} - {event.timestamp}")
                    
        except Exception as e:
            logger.error(f"Error processing log lines: {e}")
    
    def _should_generate_recommendations(self, event) -> bool:
        """Check if we should generate AI recommendations."""
        # Generate recommendations on phase changes, card plays, etc.
        if hasattr(event, 'event_type'):
            if event.event_type in ['phase_change', 'play_card', 'draw_card', 'life_change']:
                return True
        return False
    
    async def _generate_ai_recommendations(self):
        """Generate AI recommendations for the current game state."""
        try:
            # Get current game state
            game_state = self.state_integration.get_current_state()
            if not game_state:
                return
            
            # Update heuristic engine with current state
            self.heuristic_engine = HeuristicEngine(game_state)
            
            # Get AI recommendations
            recommendations = self.heuristic_engine.get_recommendations(1, max_recommendations=3)
            
            if recommendations:
                logger.info("AI Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    logger.info(f"  {i}. {rec.action.action_type} (Score: {rec.score:.2f}, Priority: {rec.priority})")
                    for reason in rec.reasoning:
                        logger.info(f"     - {reason}")
                
                # Check for emergency actions
                emergency_actions = self.heuristic_engine.get_emergency_actions(1)
                if emergency_actions:
                    logger.warning("EMERGENCY ACTIONS DETECTED:")
                    for rec in emergency_actions:
                        logger.warning(f"  - {rec.action.action_type} (Score: {rec.score:.2f})")
                        for reason in rec.reasoning:
                            logger.warning(f"    - {reason}")
            
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
    
    async def stop(self):
        """Stop the MTGA Coach."""
        try:
            logger.info("Stopping MTGA Coach...")
            
            self.is_running = False
            
            # Stop file tailer
            if self.file_tailer:
                self.file_tailer.stop()
                logger.info("File tailer stopped")
            
            # Stop state integration
            if self.state_integration:
                await self.state_integration.stop()
                logger.info("State integration stopped")
            
            logger.info("MTGA Coach stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MTGA Coach: {e}")
    
    def get_current_state(self):
        """Get the current game state."""
        if self.state_integration:
            return self.state_integration.get_current_state()
        return None
    
    def get_game_summary(self):
        """Get a summary of the current game state."""
        if self.state_integration:
            return self.state_integration.get_game_summary()
        return None
    
    def is_game_active(self) -> bool:
        """Check if a game is currently active."""
        if self.state_integration:
            return self.state_integration.is_game_active()
        return False
    
    def get_ai_recommendations(self, max_recommendations: int = 5):
        """Get AI recommendations for the current game state."""
        if self.heuristic_engine:
            return self.heuristic_engine.get_recommendations(1, max_recommendations)
        return []
    
    def get_best_ai_action(self):
        """Get the best AI action recommendation."""
        if self.heuristic_engine:
            return self.heuristic_engine.get_best_action(1)
        return None
    
    def get_board_analysis(self):
        """Get comprehensive board analysis."""
        if self.heuristic_engine:
            return self.heuristic_engine.get_board_analysis(1)
        return {}
    
    def get_emergency_ai_actions(self):
        """Get emergency AI actions for critical situations."""
        if self.heuristic_engine:
            return self.heuristic_engine.get_emergency_actions(1)
        return []

async def main():
    """Main function."""
    # Create coach instance
    coach = MTGACoachWithHeuristic()
    
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

def run_heuristic_test():
    """Run a test with heuristic evaluation."""
    print("MTGA Coach - Heuristic AI Test")
    print("=" * 40)
    
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
    from parser.log_parser import MTGALogParser
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
    
    # Test heuristic engine
    print("\nTesting heuristic engine...")
    from state.game_state import GameState
    from engine.heuristic_engine import HeuristicEngine
    
    game_state = GameState()
    game_state.initialize_game(1, 2, 20)
    heuristic_engine = HeuristicEngine(game_state)
    
    # Get AI recommendations
    recommendations = heuristic_engine.get_recommendations(1)
    print(f"\nAI Recommendations: {len(recommendations)}")
    for rec in recommendations:
        print(f"  - {rec.action.action_type} (Score: {rec.score:.2f}, Priority: {rec.priority})")
        for reason in rec.reasoning:
            print(f"    - {reason}")
    
    # Get board analysis
    analysis = heuristic_engine.get_board_analysis(1)
    print(f"\nBoard Analysis:")
    print(f"  Game status: {analysis['game_status']}")
    print(f"  Turn: {analysis['turn_number']}")
    print(f"  Phase: {analysis['current_phase']}")
    print(f"  Legal actions: {analysis['legal_actions']}")
    print(f"  Recommendations: {len(analysis['recommendations'])}")

if __name__ == "__main__":
    import os
    
    # Check if we should run heuristic test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_heuristic_test()
    else:
        # Run the main application
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
