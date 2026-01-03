# Easy Voice Memos

A cross-platform voice memo application with extensive codec support built with PySide6 and FFmpeg.

## Features

- **Multiple Codec Support**: MP3, AAC, Opus, Vorbis, FLAC, WAV, Speex, AMR
- **Flexible Quality Settings**: Configure sample rates (8kHz - 96kHz) and bit rates
- **Waveform Visualization**: Real-time waveform display during recording and playback
- **Format Conversion**: Convert recordings between different audio formats
- **File Management**: Organize, rename, delete, and search your voice memos
- **Preset Configurations**: Quick presets for voice, podcast, and music recording

## Requirements

- Python 3.11+
- FFmpeg 4.0+ (must be in PATH)
- PySide6 >= 6.6.0
- NumPy >= 1.24.0

## Installation

1. **Install FFmpeg** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg

   # macOS (using Homebrew)
   brew install ffmpeg

   # Arch Linux
   sudo pacman -S ffmpeg
   ```

2. **Install Python dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

### Recording

1. Select a recording preset from the dropdown (or use Advanced settings)
2. Click **Record** to start recording
3. Click **Pause** to pause/resume
4. Click **Stop** to finish recording
5. The recording is automatically saved and converted to your chosen format

### Playback

1. Select a memo from the list
2. Click **Play** to start playback
3. Click on the waveform to seek to a specific position
4. Use the volume slider to adjust playback volume

### File Management

Right-click on a memo in the list to:
- **Play**: Start playback
- **Rename**: Change the memo name
- **Convert Format**: Convert to a different codec
- **Show in Folder**: Open the file location
- **Delete**: Remove the memo

### Settings

Access settings via **File → Settings** or the **Advanced** button:

- **Recording Tab**: Configure codec, sample rate, bit rate, and channels
- **General Tab**: Set storage directory and file naming preferences
- **About Tab**: View FFmpeg version and supported codecs

## Codec Presets

| Preset | Codec | Sample Rate | Bit Rate | Use Case |
|--------|-------|-------------|----------|----------|
| Voice - Low Quality | Opus | 16kHz | 24kbps | Phone quality |
| Voice - Standard | Opus | 24kHz | 32kbps | Standard voice recording |
| Voice - High Quality | MP3 | 44.1kHz | 128kbps | High quality voice |
| Podcast Standard | MP3 | 44.1kHz | 96kbps | Podcast recording |
| Music - Standard | MP3 | 44.1kHz | 192kbps | Music recording |
| Music - High Quality | AAC | 48kHz | 256kbps | High quality music |
| Music - Lossless | FLAC | 48kHz | Lossless | Archival quality |
| Archival | FLAC | 48kHz | Lossless | Maximum compression |
| Uncompressed WAV | WAV | 44.1kHz | Uncompressed | Editing |

## Project Structure

```
easy-voice-memos/
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── memos/                   # Default storage for recordings
├── src/
│   ├── model/              # Business logic and data models
│   ├── view/               # UI components
│   ├── controller/         # Application logic
│   └── utils/              # Helper utilities
└── tests/                  # Unit tests
```

## Architecture

The application follows the **Model-View-Controller (MVC)** pattern:

- **Model**: Audio recording/playback, file management, codec configuration
- **View**: Qt-based UI components with custom waveform visualization
- **Controller**: Coordinates models and views, handles user interactions

## Troubleshooting

### FFmpeg not found
Ensure FFmpeg is installed and available in your PATH:
```bash
ffmpeg -version
```

### No audio input device
Check your system audio settings and ensure a microphone is connected.

### Codec not available
Some codecs may not be available depending on your FFmpeg build. Check available codecs:
```bash
ffmpeg -encoders | grep audio
```

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
