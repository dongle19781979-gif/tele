# Folder Generator (generate_folders.py)

This CLI scans an input folder, creates a subfolder per file, optionally copies the original file, and generates a per-file `README.md`. When enabled, it uses Google Gemini to generate an AI-written overview for each file.

## Setup

1. (Optional) Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set your Google API key for AI generation:
```bash
export GOOGLE_API_KEY=your_api_key_here
```

## Usage

Basic run:
```bash
python generate_folders.py ./input -o ./output
```

Include AI generation:
```bash
python generate_folders.py ./input -o ./output --use-ai --model gemini-1.5-flash
```

Copy the original file into each subfolder:
```bash
python generate_folders.py ./input -o ./output --copy-original
```

Filter by extensions:
```bash
python generate_folders.py ./input -o ./output --include-ext .py --include-ext .md
```

Recurse into subdirectories:
```bash
python generate_folders.py ./input -o ./output --recursive
```

Dry run (prints actions, no writes):
```bash
python generate_folders.py ./input -o ./output --dry-run
```

## Notes
- AI generation requires `google-generativeai` and a valid `GOOGLE_API_KEY`.
- The script writes a `metadata.json` alongside `README.md` in each generated folder.
- Binary files skip content sampling for AI and only include metadata.