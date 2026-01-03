# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Easy Voice Memos is a cross-platform voice memo application with extensive codec support built using PySide6 and FFmpeg. The application records audio initially in WAV format using Qt's QMediaRecorder, then converts to various formats (MP3, AAC, Opus, Vorbis, FLAC, WAV, Speex, AMR) via FFmpeg subprocess calls.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Must activate venv first
source .venv/bin/activate
python main.py
```

### Testing
```bash
# Run tests (when implemented)
python -m pytest tests/
python -m pytest tests/test_specific.py  # Run single test file
```

## Architecture

The application follows **strict MVC pattern**:

### Model Layer (`src/model/`)
- **AudioRecorder**: Uses PySide6 QMediaRecorder to capture audio to WAV
- **AudioPlayer**: Playback using QMediaPlayer with waveform visualization
- **FormatConverter**: Post-recording FFmpeg conversion to target codecs
- **MemoManager**: File system management for recordings
- **AudioLevelMonitor**: Real-time audio level monitoring during recording
- **WaveformData**: Manages waveform visualization data
- **CodecConfig**: Codec configuration and presets
- **Settings**: Application settings persistence

### View Layer (`src/view/`)
- **MainWindow**: Top-level application window
- **RecordingPanel**: Recording controls and preset selection
- **PlaybackWidget**: Playback controls
- **WaveformWidget**: Custom Qt widget for waveform visualization
- **MemoListWidget**: File browser for recorded memos
- **SettingsDialog**: Multi-tab settings interface
- **AppStyle**: Centralized stylesheet management

### Controller Layer (`src/controller/`)
- **MainController**: Orchestrates all components, creates and initializes sub-controllers
- **RecordingController**: Manages recording lifecycle and post-recording conversion
- **PlaybackController**: Handles playback state and waveform interaction
- **MemoController**: Manages memo list, file operations (rename, delete, convert, show in folder)

### Utilities (`src/utils/`)
- **FFmpegWrapper**: Subprocess interface for ffmpeg/ffprobe operations
- **AudioUtils**: Audio processing utilities (waveform generation, level calculations)
- **PlatformUtils**: Cross-platform file operations (open folder, etc.)

## Key Architectural Patterns

### Recording Flow
1. User initiates recording → RecordingController
2. AudioRecorder captures to temporary WAV file using QMediaRecorder
3. On stop → FormatConverter uses FFmpeg to convert WAV to target format
4. MemoManager saves file to storage directory
5. UI updates to show new memo

### FFmpeg Integration
- FFmpeg is **NOT** used for recording (Qt handles this)
- FFmpeg is used for:
  - Post-recording format conversion
  - Waveform data extraction (ffprobe for duration, ffmpeg for audio samples)
  - Format validation and codec information
- All FFmpeg calls are subprocess operations, not library bindings

### Signal/Slot Communication
Controllers connect model signals to view slots. Views emit user action signals that controllers handle. Models are decoupled from views via controller mediation.

## Dependencies

- **PySide6**: Qt6 bindings for Python (GUI, audio recording/playback)
- **NumPy**: Waveform data processing
- **FFmpeg**: External binary (must be in PATH) for format conversion

## Common Patterns

### Adding a New Codec
1. Update `CodecConfig` with codec parameters (file extension, encoder name, sample rates, bit rates)
2. Add preset to `CodecPresets` if needed
3. Update SettingsDialog codec dropdown
4. Test conversion via FormatConverter

### Adding a New Controller
1. Create in `src/controller/`
2. Instantiate in MainController.__init__()
3. Initialize in MainController.initialize()
4. Connect relevant signals between model, view, and controller

### Testing FFmpeg Operations
FFmpeg must be available in PATH. Check with:
```bash
ffmpeg -version
ffmpeg -encoders | grep audio  # List available audio codecs
```

## File Organization

- Recordings default to `memos/` directory (configurable)
- Settings stored in platform-specific locations via QSettings
- Temporary WAV files created during recording, deleted after conversion
