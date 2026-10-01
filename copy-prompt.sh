#!/bin/bash

# Script to copy a prompt file to clipboard

show_help() {
    echo "Usage: ./copy-prompt.sh [OPTIONS] <prompt-file>"
    echo ""
    echo "Copy a prompt file to your clipboard for use with any AI assistant."
    echo ""
    echo "Options:"
    echo "  --list, -l    List all available prompts with descriptions"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./copy-prompt.sh interactive-prd-creation-prompt.md"
    echo "  ./copy-prompt.sh --list"
}

show_prompts() {
    echo "Available prompts (in recommended workflow order):"
    echo ""
    echo "  interactive-prd-creation-prompt.md         Create a PRD through guided Q&A"
    echo "  prd-comprehensive-verification-prompt.md   Review and improve your PRD"
    echo "  prd-to-features-prompt.md                  Extract features from your PRD"
    echo "  prd-to-rules-prompt.md                     Generate development rules"
    echo "  prd-to-rfcs-prompt.md                      Break PRD into implementation RFCs"
    echo "  implementation-prompt-template.md          Template for implementing RFCs"
    echo "  code-review-prompt.md                      Review implementation against RFC"
    echo "  testing-strategy-prompt.md                 Generate test plan from features/RFCs"
    echo "  prd-change-management-prompt.md            Manage PRD changes mid-development"
    echo "  workflow-status-prompt.md                  Show workflow progress and next step"
    echo ""
    echo "Tip: prefer native slash commands? Run ./install.sh <your-project> to install"
    echo "these as /commands for Claude Code, Cursor, Gemini CLI, Windsurf, or OpenCode."
}

# Handle flags
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_help
    exit 0
fi

if [[ "$1" == "--list" || "$1" == "-l" ]]; then
    show_prompts
    exit 0
fi

# Check if a prompt file was specified
if [ $# -eq 0 ]; then
    echo "Usage: ./copy-prompt.sh <prompt-file>"
    echo ""
    show_prompts
    echo ""
    echo "Run ./copy-prompt.sh --help for more options."
    exit 1
fi

# Check if the file exists
if [ ! -f "$1" ]; then
    echo "Error: File '$1' not found."
    echo ""
    echo "Run ./copy-prompt.sh --list to see available prompts."
    exit 1
fi

# Copy to clipboard based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    pbcopy < "$1"
    echo "Copied '$1' to clipboard. Paste it into your AI assistant."
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v xclip > /dev/null; then
        xclip -selection clipboard < "$1"
        echo "Copied '$1' to clipboard. Paste it into your AI assistant."
    elif command -v xsel > /dev/null; then
        xsel --clipboard < "$1"
        echo "Copied '$1' to clipboard. Paste it into your AI assistant."
    else
        echo "Error: xclip or xsel is not installed. Please install one of them or copy the file contents manually."
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    clip < "$1"
    echo "Copied '$1' to clipboard. Paste it into your AI assistant."
else
    echo "Unsupported operating system. Please copy the file contents manually."
    exit 1
fi
