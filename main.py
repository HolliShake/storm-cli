import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys

from src.template import Template
from src.interpreter import Interpreter


def check_network():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
    except OSError:
        print("ERROR: No internet connection. This script requires network access.")
        sys.exit(1)
    print("  [ok] internet connection")


def check_dotnet_prerequisites():
    missing = []

    if shutil.which("dotnet") is None:
        missing.append("dotnet-sdk")
    else:
        version_result = subprocess.run(["dotnet", "--version"], capture_output=True, text=True)
        if version_result.returncode == 0:
            version = version_result.stdout.strip()
            parts = version.split(".")
            major = int(parts[0])
            if major < 8:
                missing.append(f"dotnet-sdk 8+ (found {version})")
        else:
            missing.append("dotnet-sdk (unable to determine version)")

        result = subprocess.run(["dotnet", "ef", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append("ef-core (dotnet-ef global tool)")

    if missing:
        print("ERROR: Missing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        print("\nInstall the missing dependencies and try again.")
        sys.exit(1)

    print(f"  [ok] dotnet-sdk ({version})")
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
            match = re.search(r'PHP\s+(\d+)\.', first_line)
            if match:
                major = int(match.group(1))
                if major < 12:
                    missing.append("php 12+ (found php " + first_line.split()[1] if len(first_line.split()) > 1 else "older version)")
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

    print("  [ok] php 12+")
    print("  [ok] composer")


SCHEMA_STORM = """\
// ============================================================================
//  Schema Definition — define your data model here
//  Run `python main.py --generate` after editing to rebuild all source files.
// ============================================================================

// ── Enums ──────────────────────────────────────────────────────────────────

enum Status {
    Active   = "active",
    Inactive = "inactive",
    Pending  = "pending"
}

enum Role {
    Admin = "admin",
    User  = "user"
}

// ── Tables ─────────────────────────────────────────────────────────────────

table User {
    id:       uuid pk;
    name:     string(min=2,max=100);
    email:    string(max=255) unique;
    password: string(max=255);
    role:     Role;
    status:   Status;
    createdAt:datetime;
    updatedAt:datetime;
}

table Product {
    id:      int? pk;
    name:    string(min=1,max=200);
    price:   double(min=0) = 0;
    stock:   int(min=0) = 0;
    status:  Status;
    ownerId: uuid;
    owner:   User;
    createdAt:datetime;
    updatedAt:datetime;
}
"""


CONFIGS = {
    Template.DOTNETCSHARP.value: {
        "EnumPath": "./Static",
        "ModelPath": "./Models",
        "ControllerPath": "./Controllers",
        "DtoPath": "./Dtos",
        "IServicePath": "./IServices",
        "ServicePath": "./Services",
        "MapperPath": "./Mappers",
        "DbContextPath": "./Data",
        "PaginationPath": "./Pagination",
    },
    Template.DOTNETCSHARP_CLEANARCHITECTURE.value: {
        "EnumPath": "./Static",
        "ModelPath": "./DOMAIN/Models",
        "ControllerPath": "./API/Controllers",
        "DtoPath": "./APPLICATION/Dtos",
        "IServicesPath": "./APPLICATION/IServices",
        "ServicePath": "./INFRASTRUCTURE/Services",
        "MapperPath": "./INFRASTRUCTURE/Mappers",
        "DbContextPath": "./INFRASTRUCTURE/Data",
        "PaginationPath": "./APPLICATION/Pagination",
    },
    Template.LARAVELPHP.value: {
        "EnumPath": "./app/Static",
        "ModelPath": "./app/Models",
        "ControllerPath": "./app/Controllers",
        "DtoPath": "./app/Dtos",
        "IServicePath": "./app/IServices",
        "ServicePath": "./app/Services",
        "MapperPath": "./app/Mappers",
        "MigrationsPath": "./database/migrations",
    },
}


def write_config(config, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    config_path = os.path.join(target_dir, "storm.config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"  [ok] storm.config.json written")


def create_config_dirs(config, base_dir):
    for path in config.values():
        dir_path = os.path.join(base_dir, path.lstrip("./"))
        os.makedirs(dir_path, exist_ok=True)
    print("  [ok] config directories created")


def run_dotnet(args, cwd=None):
    print(f"  [>] dotnet {' '.join(args)}")
    result = subprocess.run(["dotnet"] + args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: dotnet command failed:")
        print(result.stderr)
        sys.exit(1)


def run_composer(args, cwd=None):
    print(f"  [>] composer {' '.join(args)}")
    result = subprocess.run(["composer"] + args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: composer command failed:")
        print(result.stderr)
        sys.exit(1)


def get_dotnet_version():
    result = subprocess.run(["dotnet", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("ERROR: Could not determine dotnet SDK version")
        sys.exit(1)
    version = result.stdout.strip()
    parts = version.split(".")
    return f"{parts[0]}.{parts[1]}"


def add_nuget_package(project_csproj, package_name, version=None, cwd=None):
    args = ["add", project_csproj, "package", package_name]
    if version:
        args.extend(["--version", version])
    result = subprocess.run(["dotnet"] + args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [!!] {package_name} skipped (already present or not found)")
    else:
        print(f"  [ok] {package_name}")


NUGET_SIMPLE = [
    ("Microsoft.EntityFrameworkCore", True),
    ("Microsoft.EntityFrameworkCore.SqlServer", True),
    ("Microsoft.EntityFrameworkCore.Design", True),
    ("Microsoft.AspNetCore.Identity.EntityFrameworkCore", True),
    ("AutoMapper", False),
    ("Newtonsoft.Json", False),
    ("Scrutor", False),
    ("Swashbuckle.AspNetCore", False),
    ("Scalar.AspNetCore", False),
]

NUGET_CLEAN_ARCH = {
    "APPLICATION": [
        ("AutoMapper", False),
    ],
    "INFRASTRUCTURE": [
        ("Microsoft.EntityFrameworkCore", True),
        ("Microsoft.EntityFrameworkCore.SqlServer", True),
        ("Microsoft.AspNetCore.Identity.EntityFrameworkCore", True),
    ],
    "API": [
        ("Microsoft.EntityFrameworkCore.Design", True),
        ("Newtonsoft.Json", False),
        ("Scrutor", False),
        ("Swashbuckle.AspNetCore", False),
        ("Scalar.AspNetCore", False),
    ],
}


def install_nuget_packages(project_csproj, packages, sdk_version, cwd=None):
    for package_name, is_sdk_versioned in packages:
        version = sdk_version if is_sdk_versioned else None
        add_nuget_package(project_csproj, package_name, version=version, cwd=cwd)


def init_dotnet_project(config, project_dir, name):
    print("\nCreating dotnet webapi project...")
    run_dotnet(["new", "webapi", "-n", name, "-o", project_dir, "--force"])
    create_config_dirs(config, project_dir)

    sdk_version = get_dotnet_version()
    csproj = f"{name}.csproj"
    print(f"\nInstalling NuGet packages (SDK {sdk_version})...")
    install_nuget_packages(csproj, NUGET_SIMPLE, sdk_version, cwd=project_dir)

    write_config(config, project_dir)


def init_dotnet_clean_arch_project(config, solution_dir, name):
    print("\nCreating clean architecture solution...")

    layers = [
        ("DOMAIN", "classlib"),
        ("APPLICATION", "classlib"),
        ("INFRASTRUCTURE", "classlib"),
        ("API", "webapi"),
    ]

    for layer, project_type in layers:
        run_dotnet(["new", project_type, "-n", layer, "-o", layer, "--force"], cwd=solution_dir)

    run_dotnet(["new", "sln", "-n", name, "--force"], cwd=solution_dir)

    sln_name = f"{name}.sln"
    for layer, _ in layers:
        run_dotnet(["sln", sln_name, "add", f"{layer}/{layer}.csproj"], cwd=solution_dir)

    run_dotnet(["add", "APPLICATION/APPLICATION.csproj", "reference", "DOMAIN/DOMAIN.csproj"], cwd=solution_dir)
    run_dotnet(["add", "INFRASTRUCTURE/INFRASTRUCTURE.csproj", "reference", "APPLICATION/APPLICATION.csproj"], cwd=solution_dir)
    run_dotnet(["add", "API/API.csproj", "reference", "APPLICATION/APPLICATION.csproj"], cwd=solution_dir)
    run_dotnet(["add", "API/API.csproj", "reference", "INFRASTRUCTURE/INFRASTRUCTURE.csproj"], cwd=solution_dir)

    sdk_version = get_dotnet_version()
    print(f"\nInstalling NuGet packages (SDK {sdk_version})...")
    for layer, packages in NUGET_CLEAN_ARCH.items():
        csproj = f"{layer}/{layer}.csproj"
        install_nuget_packages(csproj, packages, sdk_version, cwd=solution_dir)

    create_config_dirs(config, solution_dir)
    write_config(config, solution_dir)


COMPOSER_PACKAGES = [
    "zircote/swagger-php",
    "spatie/laravel-query-builder",
    "spatie/laravel-medialibrary",
]


def init_laravel_project(config, project_dir):
    print("\nCreating Laravel project...")
    run_composer(["create-project", "laravel/laravel", project_dir, "--prefer-dist"])
    create_config_dirs(config, project_dir)

    print(f"\nInstalling Composer packages...")
    run_composer(["require"] + COMPOSER_PACKAGES, cwd=project_dir)

    write_config(config, project_dir)


def main():
    parser = argparse.ArgumentParser(description="API Starter Kit")

    parser.add_argument(
        "--init", "-i",
        action="store_true",
        help="Initialize a new project"
    )

    parser.add_argument(
        "--generate", "-g",
        action="store_true",
        help="Generate code from schema.storm"
    )

    template_choices = [t.value for t in Template]
    parser.add_argument(
        "--template", "-t",
        choices=template_choices,
        help=f"Project template to use (default: {template_choices[0]})"
    )

    parser.add_argument(
        "--name", "-n",
        help="Project name (defaults to current directory name)"
    )

    args = parser.parse_args()

    if args.init:
        template = args.template or template_choices[0]
        project_name = args.name or os.path.basename(os.getcwd())
        print(f"Initializing project with template: {template}")
        print(f"Project name: {project_name}")

        check_network()

        if template in (Template.DOTNETCSHARP.value, Template.DOTNETCSHARP_CLEANARCHITECTURE.value):
            check_dotnet_prerequisites()
        elif template == Template.LARAVELPHP.value:
            check_laravel_prerequisites()

        config = CONFIGS[template]

        if template == Template.DOTNETCSHARP.value:
            init_dotnet_project(config, ".", project_name)
        elif template == Template.DOTNETCSHARP_CLEANARCHITECTURE.value:
            init_dotnet_clean_arch_project(config, ".", project_name)
        elif template == Template.LARAVELPHP.value:
            init_laravel_project(config, ".")

        schema_path = os.path.join(".", "schema.storm")
        if not os.path.exists(schema_path):
            with open(schema_path, "w", encoding="utf-8") as f:
                f.write(SCHEMA_STORM)
            print("  [ok] schema.storm created")
        else:
            print("  [--] schema.storm already exists, skipped")

    elif args.generate:
        config_path = "storm.config.json"
        schema_path = args.name or "schema.storm"

        if not os.path.exists(config_path):
            print(f"ERROR: {config_path} not found. Run --init first.")
            sys.exit(1)

        if not os.path.exists(schema_path):
            print(f"ERROR: {schema_path} not found.")
            sys.exit(1)

        with open(config_path) as f:
            config = json.load(f)

        project_name = os.path.basename(os.getcwd())
        print(f"Generating code for: {project_name}")
        print(f"  config: {config_path}")
        print(f"  schema: {schema_path}")

        interpreter = Interpreter(schema_path)
        interpreter.generate(config, project_name, ".")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()