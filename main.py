"""
main.py — legacy entry point, kept for backwards compatibility.
The primary interface is now the CLI:
    autodoc run --input <path> --format md,html,pdf
Or directly:
    python main.py --input <path>
"""
import sys
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    from autodoc.cli import app
    app()


if __name__ == "__main__":
    # Support legacy: python main.py --input <path>
    if len(sys.argv) >= 2 and sys.argv[1] == "--input":
        sys.argv = [sys.argv[0], "run", "--input", sys.argv[2]]
    main()
