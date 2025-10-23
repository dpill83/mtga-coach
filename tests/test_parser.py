#!/usr/bin/env python3
"""
Test Harness for MTGA Log Parser

Tests the parser with sample log data and validates event schemas.
"""

import json
import pytest
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from parser.log_parser import MTGALogParser
from parser.events import EventType, GameEvent
from parser.log_path import MTGALogPath
from parser.file_tailer import MTGALogTailer, BufferedLogTailer
from parser.event_bus import EventBusManager

class TestMTGALogParser:
    """Test cases for the log parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MTGALogParser()
        
        # Create sample log data
        self.sample_log_lines = [
            '[UnityCrossThreadLogger] {"greToClientEvent":{"greToClientEvent":{"type":"GREMessageType_GameStateMessage","gameStateMessage":{"gameStateId":1,"turnInfo":{"turnNumber":1,"phase":"FirstMain","step":"PreCombat","activePlayer":1,"priorityPlayer":1},"zones":[{"zoneId":1,"type":"ZoneType_Battlefield","objectInstanceIds":[]},{"zoneId":2,"type":"ZoneType_Hand","objectInstanceIds":[1,2,3,4,5,6,7]}],"objects":[{"instanceId":1,"grpId":12345,"controller":1,"zoneId":2,"visibility":"Visibility_Visible","cardTypes":["CardType_Creature"],"name":"Lightning Bolt","manaCost":"{R}","power":0,"toughness":0,"abilities":[]}]}}}}',
            '[UnityCrossThreadLogger] {"greToClientEvent":{"greToClientEvent":{"type":"GREMessageType_GameStateMessage","gameStateMessage":{"gameStateId":2,"turnInfo":{"turnNumber":1,"phase":"FirstMain","step":"PreCombat","activePlayer":1,"priorityPlayer":1},"zones":[{"zoneId":1,"type":"ZoneType_Battlefield","objectInstanceIds":[]},{"zoneId":2,"type":"ZoneType_Hand","objectInstanceIds":[1,2,3,4,5,6,7]}],"objects":[{"instanceId":1,"grpId":12345,"controller":1,"zoneId":2,"visibility":"Visibility_Visible","cardTypes":["CardType_Instant"],"name":"Lightning Bolt","manaCost":"{R}","power":0,"toughness":0,"abilities":[]}]}}}}',
            '[UnityCrossThreadLogger] {"greToClientEvent":{"greToClientEvent":{"type":"GREMessageType_GameStateMessage","gameStateMessage":{"gameStateId":3,"turnInfo":{"turnNumber":1,"phase":"FirstMain","step":"PreCombat","activePlayer":1,"priorityPlayer":1},"zones":[{"zoneId":1,"type":"ZoneType_Battlefield","objectInstanceIds":[]},{"zoneId":2,"type":"ZoneType_Hand","objectInstanceIds":[1,2,3,4,5,6,7]}],"objects":[{"instanceId":1,"grpId":12345,"controller":1,"zoneId":2,"visibility":"Visibility_Visible","cardTypes":["CardType_Land"],"name":"Mountain","manaCost":"","power":0,"toughness":0,"abilities":[]}]}}}}'
        ]
    
    def test_parse_unity_log_line(self):
        """Test parsing Unity log lines."""
        for line in self.sample_log_lines:
            event = self.parser.parse_log_line(line)
            assert event is not None, f"Failed to parse line: {line[:100]}..."
            assert hasattr(event, 'event_type'), "Event should have event_type"
            assert hasattr(event, 'timestamp'), "Event should have timestamp"
    
    def test_parse_invalid_line(self):
        """Test parsing invalid log lines."""
        invalid_lines = [
            "This is not a Unity log line",
            "[UnityCrossThreadLogger] invalid json",
            "",
            "   ",
            "[UnityCrossThreadLogger] {}"
        ]
        
        for line in invalid_lines:
            event = self.parser.parse_log_line(line)
            assert event is None, f"Should not parse invalid line: {line}"
    
    def test_parse_game_state_message(self):
        """Test parsing game state messages."""
        line = self.sample_log_lines[0]
        event = self.parser.parse_log_line(line)
        
        assert event is not None, "Should parse game state message"
        assert event.event_type in [EventType.PHASE_CHANGE, EventType.DRAW_CARD], f"Unexpected event type: {event.event_type}"
    
    def test_parse_multiple_lines(self):
        """Test parsing multiple log lines."""
        events = self.parser.parse_log_lines(self.sample_log_lines)
        
        assert len(events) > 0, "Should parse at least one event"
        assert all(isinstance(event, GameEvent) for event in events), "All events should be GameEvent instances"
    
    def test_event_timestamps(self):
        """Test that events have valid timestamps."""
        events = self.parser.parse_log_lines(self.sample_log_lines)
        
        for event in events:
            assert isinstance(event.timestamp, datetime), "Event should have datetime timestamp"
            assert event.timestamp <= datetime.now(), "Event timestamp should not be in the future"

class TestLogPathDetection:
    """Test cases for log path detection."""
    
    def test_detect_log_path(self):
        """Test log path detection."""
        detector = MTGALogPath()
        
        # Test with auto detection
        path = detector.detect_log_path()
        # Path might be None if MTGA not installed, which is OK for testing
        
        # Test with custom path
        custom_path = "tests/sample_logs/test_log.txt"
        path = detector.detect_log_path(custom_path)
        # Should return None since file doesn't exist
    
    def test_create_sample_log(self):
        """Test creating sample log file."""
        detector = MTGALogPath()
        
        # Create sample log
        success = detector.create_sample_log()
        assert success, "Should create sample log successfully"
        
        # Check if file exists
        sample_path = detector.get_sample_log_path()
        assert sample_path.exists(), "Sample log file should exist"
        
        # Validate the file
        assert detector.validate_log_file(sample_path), "Sample log should be valid"

class TestFileTailer:
    """Test cases for file tailer."""
    
    def test_tailer_creation(self):
        """Test creating file tailer."""
        sample_path = Path("tests/sample_logs/sample_output_log.txt")
        
        # Create tailer
        tailer = MTGALogTailer(sample_path, lambda line: None)
        assert tailer is not None, "Should create tailer"
    
    def test_buffered_tailer_creation(self):
        """Test creating buffered tailer."""
        sample_path = Path("tests/sample_logs/sample_output_log.txt")
        
        # Create buffered tailer
        tailer = BufferedLogTailer(sample_path, lambda lines: None)
        assert tailer is not None, "Should create buffered tailer"

class TestEventBus:
    """Test cases for event bus."""
    
    @pytest.mark.asyncio
    async def test_event_bus_creation(self):
        """Test creating event bus."""
        event_bus = EventBusManager(port=8766)  # Use different port for testing
        assert event_bus is not None, "Should create event bus"
        
        # Test starting and stopping
        await event_bus.start()
        assert event_bus.event_bus.is_running, "Event bus should be running"
        
        await event_bus.stop()
        assert not event_bus.event_bus.is_running, "Event bus should be stopped"
    
    @pytest.mark.asyncio
    async def test_event_broadcasting(self):
        """Test event broadcasting."""
        from parser.events import GameStartEvent, EventType
        
        event_bus = EventBusManager(port=8767)  # Use different port for testing
        
        try:
            await event_bus.start()
            
            # Create test event
            test_event = GameStartEvent(
                event_type=EventType.GAME_START,
                player_life=20,
                opponent_life=20
            )
            
            # Queue event (should not raise exception)
            await event_bus.queue_event(test_event)
            
        finally:
            await event_bus.stop()

def test_integration():
    """Integration test for the entire parser pipeline."""
    # Create sample log
    detector = MTGALogPath()
    if not detector.create_sample_log():
        pytest.skip("Could not create sample log")
    
    # Parse sample log
    parser = MTGALogParser()
    sample_path = detector.get_sample_log_path()
    
    events = []
    with open(sample_path, 'r') as f:
        for line in f:
            event = parser.parse_log_line(line)
            if event:
                events.append(event)
    
    # Should have parsed some events
    assert len(events) > 0, "Should parse events from sample log"
    
    # All events should be valid
    for event in events:
        assert isinstance(event, GameEvent), "All events should be GameEvent instances"
        assert event.event_type is not None, "All events should have event type"
        assert event.timestamp is not None, "All events should have timestamp"

def run_manual_tests():
    """Run manual tests that require user interaction."""
    print("MTGA Coach - Manual Tests")
    print("=" * 30)
    
    # Test 1: Log path detection
    print("1. Testing log path detection...")
    detector = MTGALogPath()
    log_path = detector.detect_log_path()
    if log_path:
        print(f"   Found MTGA log: {log_path}")
    else:
        print("   No MTGA log found (this is OK for testing)")
    
    # Test 2: Sample log creation
    print("2. Testing sample log creation...")
    if detector.create_sample_log():
        print("   Sample log created successfully")
    else:
        print("   Failed to create sample log")
    
    # Test 3: Parser with sample data
    print("3. Testing parser with sample data...")
    parser = MTGALogParser()
    sample_path = detector.get_sample_log_path()
    
    if sample_path.exists():
        events = []
        with open(sample_path, 'r') as f:
            for line in f:
                event = parser.parse_log_line(line)
                if event:
                    events.append(event)
        
        print(f"   Parsed {len(events)} events from sample log")
        for i, event in enumerate(events[:3]):  # Show first 3 events
            print(f"     Event {i+1}: {event.event_type} at {event.timestamp}")
    else:
        print("   Sample log not found")
    
    print("Manual tests completed!")

if __name__ == "__main__":
    # Run manual tests
    run_manual_tests()
