import argparse
import shutil
import subprocess
import sys

from src.template import Template


def check_dotnet_prerequisites():
    missing = []

    if shutil.which("dotnet") is None:
        missing.append("dotnet-sdk")
    else:
        result = subprocess.run(["dotnet", "ef", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append("ef-core (dotnet-ef global tool)")

    if missing:
        print("ERROR: Missing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        print("\nInstall the missing dependencies and try again.")
        sys.exit(1)

    print("  [ok] dotnet-sdk")
    print("  [ok] ef-core")


def check_laravel_prerequisites():
    missing = []

    php_path = shutil.which("php") or shutil.which("php-win")
    if php_path is None:
        missing.append("php / php-win")
    else:
        result = subprocess.run([php_path, "-v"], capture_output=True, text=True)
        if result.returncode == 0:
            first_line = result.stdout.splitlines()[0]
            import re
            match = re.search(r'PHP\s+(\d+)\.', first_line)
            if match:
                major = int(match.group(1))
                if major < 8:
                    missing.append("php 8+ (found php " + first_line.split()[1] if len(first_line.split()) > 1 else "older version)")
            else:
                missing.append("php (unable to determine version)")
        else:
            missing.append("php (not working)")

    if shutil.which("composer") is None:
        missing.append("composer")

    if missing:
        print("ERROR: Missing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        print("\nInstall the missing dependencies and try again.")
        sys.exit(1)

    print("  [ok] php 8+")
    print("  [ok] composer")


def main():
    parser = argparse.ArgumentParser(description="API Starter Kit")

    parser.add_argument(
        "--init", "-i",
        action="store_true",
        help="Initialize a new project"
    )

    template_choices = [t.value for t in Template]
    parser.add_argument(
        "--template", "-t",
        choices=template_choices,
        help=f"Project template to use (default: {template_choices[0]})"
    )

    args = parser.parse_args()

    if args.init:
        template = args.template or template_choices[0]
        print(f"Initializing project with template: {template}")

        if template in (Template.DOTNETCSHARP.value, Template.DOTNETCSHARP_CLEANARCHITECTURE.value):
            check_dotnet_prerequisites()
        elif template == Template.LARAVELPHP.value:
            check_laravel_prerequisites()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()