# Kiri - Personal AI Assistant

**Local. Open. Yours.**

Kiri is a powerful, AI-driven personal assistant that respects your privacy above all else. It operates entirely locally, ensures every action is reversible, and never sends your personal data to the cloud.

## Features

- 🔒 **Security First**: Secret Scanner runs before ANY data is processed
- 📁 **File Organization**: Automatic file sorting with Git backup
- 📧 **Email Intelligence**: Read-only IMAP summaries and reminders
- 📊 **Daily Briefing**: Local HTML summary of your day
- 🧠 **Local AI**: Powered by Qwen 2.5 3B via Ollama
- 🔄 **Reversible**: Every action backed up via Git

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/kiri.git
cd kiri

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the default config:
   ```bash
   cp config/default.yaml config/config.yaml
   ```

2. Edit `config/config.yaml` with your settings

3. Set up credentials in your OS Keychain (not in config files!)

## Usage

```bash
# Run Kiri
python src/main.py

# Run tests
pytest tests/
```

## License

AGPL-3.0 - See LICENSE file for details

## Documentation

See [docs/](docs/) for detailed documentation including:
- User Guide
- Security Policy
- Developer Guide
- API Reference