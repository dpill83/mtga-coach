#!/usr/bin/env python3
"""
File Tailer

Real-time file monitoring for MTGA log files using watchdog.
Handles file rotation and maintains position cursor.
"""

import os
import time
import logging
from pathlib import Path
from typing import Callable, Optional, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)

class LogFileHandler(FileSystemEventHandler):
    """File system event handler for log files."""
    
    def __init__(self, callback: Callable[[str], None], file_path: Path):
        self.callback = callback
        self.file_path = file_path
        self.last_position = 0
        self.file_size = 0
        
        # Initialize position if file exists
        if file_path.exists():
            self.last_position = file_path.stat().st_size
            self.file_size = self.last_position
    
    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent) and event.src_path == str(self.file_path):
            self._read_new_content()
    
    def _read_new_content(self):
        """Read new content from the file."""
        try:
            if not self.file_path.exists():
                logger.warning(f"Log file disappeared: {self.file_path}")
                return
            
            current_size = self.file_path.stat().st_size
            
            # Handle file truncation (rotation)
            if current_size < self.last_position:
                logger.info(f"Log file truncated, resetting position: {self.file_path}")
                self.last_position = 0
                self.file_size = current_size
            
            # Read new content
            if current_size > self.last_position:
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    
                    if new_content:
                        # Split into lines and process
                        lines = new_content.splitlines()
                        for line in lines:
                            if line.strip():  # Skip empty lines
                                self.callback(line)
                    
                    self.last_position = f.tell()
                    self.file_size = current_size
            
        except Exception as e:
            logger.error(f"Error reading log file: {e}")

class MTGALogTailer:
    """Real-time MTGA log file tailer."""
    
    def __init__(self, file_path: Path, callback: Callable[[str], None]):
        self.file_path = file_path
        self.callback = callback
        self.observer = None
        self.handler = None
        self.is_running = False
        
    def start(self) -> bool:
        """Start tailing the log file."""
        try:
            if not self.file_path.exists():
                logger.error(f"Log file does not exist: {self.file_path}")
                return False
            
            # Create file handler
            self.handler = LogFileHandler(self.callback, self.file_path)
            
            # Create observer
            self.observer = Observer()
            self.observer.schedule(
                self.handler,
                str(self.file_path.parent),
                recursive=False
            )
            
            # Start observer
            self.observer.start()
            self.is_running = True
            
            logger.info(f"Started tailing log file: {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start log tailer: {e}")
            return False
    
    def stop(self):
        """Stop tailing the log file."""
        try:
            if self.observer and self.is_running:
                self.observer.stop()
                self.observer.join()
                self.is_running = False
                logger.info("Stopped log tailer")
                
        except Exception as e:
            logger.error(f"Error stopping log tailer: {e}")
    
    def is_alive(self) -> bool:
        """Check if tailer is still running."""
        return self.is_running and self.observer and self.observer.is_alive()
    
    def get_file_position(self) -> int:
        """Get current file position."""
        if self.handler:
            return self.handler.last_position
        return 0

class BufferedLogTailer:
    """Buffered log tailer that batches events for efficiency."""
    
    def __init__(self, file_path: Path, callback: Callable[[List[str]], None], 
                 batch_size: int = 10, flush_interval: float = 1.0):
        self.file_path = file_path
        self.batch_callback = callback
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.last_flush = time.time()
        
        # Create internal callback
        self._internal_callback = self._buffer_line
        
        # Create tailer
        self.tailer = MTGALogTailer(file_path, self._internal_callback)
    
    def _buffer_line(self, line: str):
        """Buffer a single line."""
        self.buffer.append(line)
        
        # Check if we should flush
        current_time = time.time()
        should_flush = (
            len(self.buffer) >= self.batch_size or
            (current_time - self.last_flush) >= self.flush_interval
        )
        
        if should_flush:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """Flush the buffer."""
        if self.buffer:
            self.batch_callback(self.buffer.copy())
            self.buffer.clear()
            self.last_flush = time.time()
    
    def start(self) -> bool:
        """Start the buffered tailer."""
        return self.tailer.start()
    
    def stop(self):
        """Stop the buffered tailer."""
        # Flush any remaining buffer
        self._flush_buffer()
        self.tailer.stop()
    
    def is_alive(self) -> bool:
        """Check if tailer is alive."""
        return self.tailer.is_alive()

def test_tailer():
    """Test function for the log tailer."""
    def line_callback(line: str):
        print(f"New line: {line}")
    
    def batch_callback(lines: List[str]):
        print(f"Batch of {len(lines)} lines:")
        for line in lines:
            print(f"  {line}")
    
    # Test with sample log
    sample_path = Path("tests/sample_logs/sample_output_log.txt")
    
    if not sample_path.exists():
        print(f"Sample log not found: {sample_path}")
        return
    
    print("Testing basic tailer...")
    tailer = MTGALogTailer(sample_path, line_callback)
    
    if tailer.start():
        print("Tailer started successfully")
        time.sleep(2)
        tailer.stop()
        print("Tailer stopped")
    
    print("\nTesting buffered tailer...")
    buffered_tailer = BufferedLogTailer(sample_path, batch_callback)
    
    if buffered_tailer.start():
        print("Buffered tailer started successfully")
        time.sleep(2)
        buffered_tailer.stop()
        print("Buffered tailer stopped")

if __name__ == "__main__":
    test_tailer()
