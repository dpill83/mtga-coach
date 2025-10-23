#!/usr/bin/env python3
"""
MTGA Log Path Detection

Detects MTGA installation path on Windows and provides fallback for test files.
"""

import os
import platform
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class MTGALogPath:
    def __init__(self):
        self.system = platform.system()
        self.default_paths = self._get_default_paths()
    
    def _get_default_paths(self) -> list:
        """Get default MTGA log paths based on operating system."""
        if self.system == "Windows":
            return [
                # Standard Windows path - Player.log (active game log)
                Path(os.environ.get("APPDATA", "")) / "LocalLow" / "Wizards Of The Coast" / "MTGA" / "Player.log",
                # Previous game log
                Path(os.environ.get("APPDATA", "")) / "LocalLow" / "Wizards Of The Coast" / "MTGA" / "Player-prev.log",
                # Alternative path - Player.log
                Path(os.environ.get("LOCALAPPDATA", "")) / "Wizards Of The Coast" / "MTGA" / "Player.log",
                # Legacy output_log.txt paths
                Path(os.environ.get("APPDATA", "")) / "LocalLow" / "Wizards Of The Coast" / "MTGA" / "output_log.txt",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Wizards Of The Coast" / "MTGA" / "output_log.txt",
                # Steam installation path
                Path(os.environ.get("PROGRAMFILES", "")) / "Steam" / "steamapps" / "common" / "MTGA" / "Player.log"
            ]
        elif self.system == "Darwin":  # macOS
            return [
                Path.home() / "Library" / "Logs" / "Wizards Of The Coast" / "MTGA" / "output_log.txt"
            ]
        else:  # Linux
            return [
                Path.home() / ".local" / "share" / "Wizards Of The Coast" / "MTGA" / "output_log.txt"
            ]
    
    def detect_log_path(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """
        Detect MTGA log file path.
        
        Args:
            custom_path: Optional custom path to use instead of auto-detection
            
        Returns:
            Path to log file if found, None otherwise
        """
        if custom_path:
            path = Path(custom_path)
            if path.exists() and path.is_file():
                logger.info(f"Using custom log path: {path}")
                return path
            else:
                logger.warning(f"Custom log path not found: {path}")
                return None
        
        # Try default paths
        for path in self.default_paths:
            if path and path.exists() and path.is_file():
                logger.info(f"Found MTGA log at: {path}")
                return path
        
        logger.warning("MTGA log file not found in default locations")
        return None
    
    def get_sample_log_path(self) -> Path:
        """Get path to sample log file for testing."""
        return Path("tests/sample_logs/sample_output_log.txt")
    
    def create_sample_log(self) -> bool:
        """Create a sample log file for testing if it doesn't exist."""
        sample_path = self.get_sample_log_path()
        
        if sample_path.exists():
            logger.info(f"Sample log already exists: {sample_path}")
            return True
        
        # Create sample log content
        sample_content = """[UnityCrossThreadLogger] {"greToClientEvent":{"greToClientEvent":{"type":"GREMessageType_GameStateMessage","gameStateMessage":{"gameStateId":1,"turnInfo":{"turnNumber":1,"phase":"FirstMain","step":"PreCombat","activePlayer":1,"priorityPlayer":1},"zones":[{"zoneId":1,"type":"ZoneType_Battlefield","objectInstanceIds":[]},{"zoneId":2,"type":"ZoneType_Hand","objectInstanceIds":[1,2,3,4,5,6,7]}],"objects":[{"instanceId":1,"grpId":12345,"controller":1,"zoneId":2,"visibility":"Visibility_Visible","cardTypes":["CardType_Creature"],"name":"Lightning Bolt","manaCost":"{R}","power":0,"toughness":0,"abilities":[]}]}}}}
[UnityCrossThreadLogger] {"greToClientEvent":{"greToClientEvent":{"type":"GREMessageType_GameStateMessage","gameStateMessage":{"gameStateId":2,"turnInfo":{"turnNumber":1,"phase":"FirstMain","step":"PreCombat","activePlayer":1,"priorityPlayer":1},"zones":[{"zoneId":1,"type":"ZoneType_Battlefield","objectInstanceIds":[]},{"zoneId":2,"type":"ZoneType_Hand","objectInstanceIds":[1,2,3,4,5,6,7]}],"objects":[{"instanceId":1,"grpId":12345,"controller":1,"zoneId":2,"visibility":"Visibility_Visible","cardTypes":["CardType_Instant"],"name":"Lightning Bolt","manaCost":"{R}","power":0,"toughness":0,"abilities":[]}]}}}}
"""
        
        try:
            # Ensure directory exists
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write sample content
            with open(sample_path, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            
            logger.info(f"Created sample log file: {sample_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create sample log: {e}")
            return False
    
    def validate_log_file(self, path: Path) -> bool:
        """Validate that the log file is readable and contains MTGA log format."""
        try:
            if not path.exists() or not path.is_file():
                return False
            
            # Check if file is readable
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first few lines to check format
                for i, line in enumerate(f):
                    if i >= 10:  # Check first 10 lines
                        break
                    if "[UnityCrossThreadLogger]" in line and "greToClientEvent" in line:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate log file {path}: {e}")
            return False

def main():
    """Test the log path detection."""
    detector = MTGALogPath()
    
    print("MTGA Log Path Detection")
    print("=" * 30)
    
    # Try to detect real log
    log_path = detector.detect_log_path()
    if log_path:
        print(f"Found MTGA log: {log_path}")
        if detector.validate_log_file(log_path):
            print("Log file validation: PASSED")
        else:
            print("Log file validation: FAILED")
    else:
        print("No MTGA log found")
    
    # Create sample log
    print("\nCreating sample log for testing...")
    if detector.create_sample_log():
        print(f"Sample log created: {detector.get_sample_log_path()}")
    else:
        print("Failed to create sample log")

if __name__ == "__main__":
    main()
