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
            match = re.search(r'PHP\s+(\d+)\.(\d+)', first_line)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                if major < 8 or (major == 8 and minor < 5):
                    missing.append("php 8.5+ (found php " + first_line.split()[1] if len(first_line.split()) > 1 else "older version)")
            else:
                missing.append("php (unable to determine version)")
        else:
            missing.append("php (not working)")

    if resolve_composer() is None:
        missing.append("composer")

    if missing:
        print("ERROR: Missing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        print("\nInstall the missing dependencies and try again.")
        sys.exit(1)

    print("  [ok] php 8.5+")
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
    },
    Template.DOTNETCSHARP_CLEANARCHITECTURE.value: {
        "EnumPath": "./DOMAIN/Static",
        "ModelPath": "./DOMAIN/Models",
        "ControllerPath": "./API/Controllers",
        "DtoPath": "./APPLICATION/Dtos",
        "IServicesPath": "./APPLICATION/IServices",
        "ServicePath": "./INFRASTRUCTURE/Services",
        "MapperPath": "./INFRASTRUCTURE/Mappers",
        "DbContextPath": "./INFRASTRUCTURE/Data",
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


def resolve_composer():
    """Find the composer executable path."""
    for name in ["composer", "composer.bat", "composer.phar"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def run_composer(args, cwd=None, ignore_platform_reqs=None):
    composer_exe = resolve_composer()
    if composer_exe is None:
        print("ERROR: composer not found. Install Composer and try again.")
        sys.exit(1)
    cmd = [composer_exe] + args
    if ignore_platform_reqs:
        for req in ignore_platform_reqs:
            cmd.append(f"--ignore-platform-req={req}")
    print(f"  [>] composer {' '.join(args)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
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
    "DOMAIN": [
        ("Microsoft.AspNetCore.Identity.EntityFrameworkCore", True),
    ],
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
    write_program_cs(PROGRAM_CS_SIMPLE, project_dir, name)

    # Update appsettings.json with ConnectionStrings
    appsettings = os.path.join(project_dir, "appsettings.json")
    if os.path.exists(appsettings):
        with open(appsettings) as f:
            cfg = json.load(f)
        cfg.setdefault("ConnectionStrings", {})["DefaultConnection"] = \
            "Server=(localdb)\\mssqllocaldb;Database=" + name + ";Trusted_Connection=True;MultipleActiveResultSets=true"
        with open(appsettings, "w") as f:
            json.dump(cfg, f, indent=2)
        print("  [ok] appsettings.json patched")


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
    write_program_cs(PROGRAM_CS_CLEAN_ARCH, os.path.join(solution_dir, "API"), name)


PROGRAM_CS_SIMPLE = """\
using System.Reflection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Scrutor;
using Scalar.AspNetCore;
using $$NAMESPACE$$.Data;
using $$NAMESPACE$$.IServices;
using $$NAMESPACE$$.Services;
using $$NAMESPACE$$.Mappers;
using $$NAMESPACE$$.Models;

var builder = WebApplication.CreateBuilder(args);

// ── Database ─────────────────────────────────────────────────────────
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

// ── Identity ────────────────────────────────────────────────────────
builder.Services.AddIdentity<User, IdentityRole<Guid>>()
    .AddEntityFrameworkStores<AppDbContext>()
    .AddTokenProvider<DataProtectorTokenProvider<User>>(TokenOptions.DefaultProvider)
    .AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(options =>
{
    options.Cookie.Name = "authToken";
    options.Cookie.HttpOnly = true;
    options.Cookie.IsEssential = true;
    options.Cookie.MaxAge = TimeSpan.FromDays(7);
    options.Cookie.Path = "/";
    options.Cookie.SameSite = SameSiteMode.None;
    var isProduction = string.Equals(
        Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Development",
        "Production", StringComparison.OrdinalIgnoreCase);
    options.Cookie.SecurePolicy = isProduction
        ? CookieSecurePolicy.Always
        : CookieSecurePolicy.SameAsRequest;
});

builder.Services.Configure<IdentityOptions>(options =>
{
    options.Password.RequireDigit = false;
    options.Password.RequireLowercase = false;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase = false;
    options.Password.RequiredLength = 3;
    options.Password.RequiredUniqueChars = 0;
    options.User.RequireUniqueEmail = true;
});

// ── AutoMapper ──────────────────────────────────────────────────────
builder.Services.AddAutoMapper(cfg =>
{
    cfg.AddMaps(Assembly.GetExecutingAssembly());
});

// ── Scrutor — register all I*Service → *Service ────────────────────
builder.Services.Scan(scan => scan
    .FromAssemblyOf<UserService>()
    .AddClasses(classes => classes
        .InNamespaces("$$NAMESPACE$$.Services")
        .AssignableTo(typeof(GenericService<,,,>)))
    .AsImplementedInterfaces()
    .WithScopedLifetime());

// ── Controllers ─────────────────────────────────────────────────────
builder.Services.AddControllers();

// ── OpenAPI / Scalar ────────────────────────────────────────────────
builder.Services.AddOpenApi();

var app = builder.Build();

// ── Swagger / Scalar ────────────────────────────────────────────────
app.UseSwagger(options =>
{
    options.RouteTemplate = "openapi/{documentName}.json";
});
app.MapScalarApiReference(options =>
{
    options.WithTitle("$$NAMESPACE$$");
    options.WithTheme(ScalarTheme.BluePlanet);
    options.WithDefaultHttpClient(ScalarTarget.JavaScript, ScalarClient.Axios);
    options.WithPreferredScheme("Bearer");
});

app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
"""

PROGRAM_CS_CLEAN_ARCH = """\
using System.Reflection;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Scrutor;
using Scalar.AspNetCore;
using $$NAMESPACE$$.DOMAIN.Models;
using $$NAMESPACE$$.APPLICATION.IServices;
using $$NAMESPACE$$.APPLICATION.Dtos.Shared;
using $$NAMESPACE$$.INFRASTRUCTURE.Data;
using $$NAMESPACE$$.INFRASTRUCTURE.Services;
using $$NAMESPACE$$.INFRASTRUCTURE.Mappers;

var builder = WebApplication.CreateBuilder(args);

// ── Database ─────────────────────────────────────────────────────────
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

// ── Identity ────────────────────────────────────────────────────────
builder.Services.AddIdentity<User, IdentityRole<Guid>>()
    .AddEntityFrameworkStores<AppDbContext>()
    .AddTokenProvider<DataProtectorTokenProvider<User>>(TokenOptions.DefaultProvider)
    .AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(options =>
{
    options.Cookie.Name = "authToken";
    options.Cookie.HttpOnly = true;
    options.Cookie.IsEssential = true;
    options.Cookie.MaxAge = TimeSpan.FromDays(7);
    options.Cookie.Path = "/";
    options.Cookie.SameSite = SameSiteMode.None;
    var isProduction = string.Equals(
        Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Development",
        "Production", StringComparison.OrdinalIgnoreCase);
    options.Cookie.SecurePolicy = isProduction
        ? CookieSecurePolicy.Always
        : CookieSecurePolicy.SameAsRequest;
});

builder.Services.Configure<IdentityOptions>(options =>
{
    options.Password.RequireDigit = false;
    options.Password.RequireLowercase = false;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase = false;
    options.Password.RequiredLength = 3;
    options.Password.RequiredUniqueChars = 0;
    options.User.RequireUniqueEmail = true;
});

// ── AutoMapper ──────────────────────────────────────────────────────
builder.Services.AddAutoMapper(cfg =>
{
    cfg.AddMaps(Assembly.GetExecutingAssembly());
});

// ── Scrutor — register all I*Service → *Service ────────────────────
builder.Services.Scan(scan => scan
    .FromAssemblyOf<UserService>()
    .AddClasses(classes => classes
        .InNamespaces("$$NAMESPACE$$.INFRASTRUCTURE.Services")
        .AssignableTo(typeof(GenericService<,,,>)))
    .AsImplementedInterfaces()
    .WithScopedLifetime());

// ── Controllers ─────────────────────────────────────────────────────
builder.Services.AddControllers();

// ── OpenAPI / Scalar ────────────────────────────────────────────────
builder.Services.AddOpenApi();

var app = builder.Build();

// ── Swagger / Scalar ────────────────────────────────────────────────
app.UseSwagger(options =>
{
    options.RouteTemplate = "openapi/{documentName}.json";
});
app.MapScalarApiReference(options =>
{
    options.WithTitle("$$NAMESPACE$$");
    options.WithTheme(ScalarTheme.BluePlanet);
    options.WithDefaultHttpClient(ScalarTarget.JavaScript, ScalarClient.Axios);
    options.WithPreferredScheme("Bearer");
});

app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
"""


def write_program_cs(template: str, project_dir: str, namespace_name: str):
    content = template.replace("$$NAMESPACE$$", namespace_name)
    path = os.path.join(project_dir, "Program.cs")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [ok] Program.cs updated")


COMPOSER_PACKAGES = [
    "zircote/swagger-php",
    "spatie/laravel-query-builder",
    "spatie/laravel-medialibrary",
]


def set_laravel_php_requirements(project_dir):
    """Set PHP ^8.5 and Laravel ^12.0 requirements in composer.json."""
    composer_path = os.path.join(project_dir, "composer.json")
    if not os.path.exists(composer_path):
        print("  [!!] composer.json not found, skipping version requirements")
        return

    with open(composer_path, "r", encoding="utf-8") as f:
        composer = json.load(f)

    composer.setdefault("require", {})
    composer["require"]["php"] = "^8.5"

    # Detect the installed Laravel version from composer.lock, fall back to ^13.0
    lock_path = os.path.join(project_dir, "composer.lock")
    laravel_constraint = "^13.0"
    if os.path.exists(lock_path):
        with open(lock_path, "r", encoding="utf-8") as f:
            lock = json.load(f)
        for pkg in lock.get("packages", []):
            if pkg.get("name") == "laravel/framework":
                version = pkg.get("version", "")
                match = re.search(r'^(\d+)\.', version)
                if match:
                    laravel_constraint = f"^{match.group(1)}.0"
                break
    composer["require"]["laravel/framework"] = laravel_constraint

    with open(composer_path, "w", encoding="utf-8") as f:
        json.dump(composer, f, indent=4)
    print(f"  [ok] composer.json updated: php ^8.5, laravel {laravel_constraint}")


def merge_temp_project(temp_dir, target_dir):
    """Move all files from temp_dir into target_dir, then remove temp_dir."""
    for item in os.listdir(temp_dir):
        src = os.path.join(temp_dir, item)
        dst = os.path.join(target_dir, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
        else:
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
    os.rmdir(temp_dir)


def init_laravel_project(config, project_dir):
    temp_dir = os.path.join(project_dir, "__laravel_temp__")
    print("\nCreating Laravel project in temporary directory...")
    run_composer([
        "create-project", "laravel/laravel", temp_dir, "--prefer-dist",
        "--ignore-platform-req=ext-fileinfo",
    ])
    print("  [ok] Laravel project created")

    merge_temp_project(temp_dir, project_dir)
    print("  [ok] project files merged into root")

    create_config_dirs(config, project_dir)

    set_laravel_php_requirements(project_dir)

    print(f"\nInstalling Composer packages...")
    run_composer(
        ["require"] + COMPOSER_PACKAGES,
        cwd=project_dir,
        ignore_platform_reqs=["ext-fileinfo", "ext-exif", "ext-gd", "ext-imagick"],
    )

    write_config(config, project_dir)


BANNER = r"""
███████ ████████  ██████  ██████  ███    ███ 
██         ██    ██    ██ ██   ██ ████  ████ 
███████    ██    ██    ██ ██████  ██ ████ ██ 
     ██    ██    ██    ██ ██   ██ ██  ██  ██ 
███████    ██     ██████  ██   ██ ██      ██ 
                                             
                                             
             ██████ ██      ██               
            ██      ██      ██               
            ██      ██      ██               
            ██      ██      ██               
             ██████ ███████ ██               
                                             
                                             
"""

YEL = "\033[33m"
RST = "\033[0m"

HELP_BANNER = f"""{YEL}
███████ ████████  ██████  ██████  ███    ███ 
██         ██    ██    ██ ██   ██ ████  ████ 
███████    ██    ██    ██ ██████  ██ ████ ██ 
     ██    ██    ██    ██ ██   ██ ██  ██  ██ 
███████    ██     ██████  ██   ██ ██      ██ 
                                             
                                             
             ██████ ██      ██               
            ██      ██      ██               
            ██      ██      ██               
            ██      ██      ██               
             ██████ ███████ ██               
                                             
                                             
  API Starter Kit -- schema to source{RST}
"""


def main():
    parser = argparse.ArgumentParser(
        description=HELP_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

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
        print(YEL + BANNER + RST)
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
        print(YEL + BANNER + RST)
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