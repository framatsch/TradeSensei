import argparse
import sys
from pathlib import Path

def merge_markdown_files(input_dirs, output_filename):
    output_path = Path(output_filename)

    # Sicherstellen, dass die Ausgabedatei nicht als Eingabedatei gelesen wird
    abs_output_path = output_path.absolute()

    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for directory in input_dirs:
                dir_path = Path(directory)

                if not dir_path.is_dir():
                    print(f"Error: Path is not a directory: {directory}", file=sys.stderr)
                    continue

                # Rekursive Suche nach .md Dateien
                for file_path in dir_path.rglob('*.md'):
                    if file_path.absolute() == abs_output_path:
                        continue

                    print("Concatenating file:", file_path)
                    # Visueller Separator
                    separator = (
                        f"\n\n{'=' * 80}\n"
                        f"SOURCE: {file_path.absolute()}\n"
                        f"{'=' * 80}\n\n"
                    )
                    outfile.write(separator)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"\n[Error reading file {file_path}: {e}]\n")

        print(f"Process completed. Combined file saved as: {abs_output_path}")

    except PermissionError:
        print(f"Error: Permission denied when writing to {output_filename}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Recursively merge Markdown files from multiple directories into one file."
    )
    parser.add_argument(
        "-d", "--directories",
        nargs="+",
        help="One or more directories to search for Markdown files."
    )
    parser.add_argument(
        "-o", "--output",
        default="out.md",
        help="The name of the output file (default: out.md)."
    )

    args = parser.parse_args()
    merge_markdown_files(args.directories, args.output)

if __name__ == "__main__":
    main()