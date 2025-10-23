# MTGA AI Coach - Batch Files

## 📁 Essential Batch Files

### 1. `setup_ai_coach.bat` - **First Time Setup**
- **Run this FIRST** before using the AI Coach
- Installs all Python dependencies
- Downloads Scryfall card data
- Runs tests to verify everything works

### 2. `run_ai_coach.bat` - **Start AI Coach**
- **Main launcher** for the AI Coach
- Starts monitoring your MTGA games
- Provides real-time AI recommendations
- **Use this after setup is complete**

### 3. `test_ai_coach.bat` - **Test AI System**
- Tests the AI Coach with sample data
- Verifies the system is working
- **Use this to test without playing MTGA**

### 4. `check_mtga_log.bat` - **Check Log Files**
- Checks if MTGA log files exist
- Shows where to find Player.log
- **Use this if AI Coach can't find your log files**

## 🚀 Quick Start Guide

1. **First time:** Run `setup_ai_coach.bat`
2. **Start MTGA Arena** and begin a match
3. **Run `run_ai_coach.bat`** to start AI coaching
4. **Watch for AI recommendations** in the terminal

## 🎯 What You'll See

When the AI Coach is working, you'll see:
```
AI Recommendations:
  1. CAST_SPELL (Score: 8.50, Priority: high)
     - Lightning Bolt can deal lethal damage
     - Efficient mana cost
  2. DECLARE_ATTACKERS (Score: 6.20, Priority: medium)
     - Attackers deal 5 damage
     - Flying attackers
```

## 🔧 Troubleshooting

- **Can't find log files?** Run `check_mtga_log.bat`
- **Want to test?** Run `test_ai_coach.bat`
- **Need to reinstall?** Run `setup_ai_coach.bat`

## 📋 Requirements

- Python 3.8+ installed
- MTGA Arena installed and running
- Active match in MTGA (for real-time coaching)
