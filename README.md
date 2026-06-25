# API Starter Kit

A CLI tool that scaffolds full-stack API projects from a declarative schema file. Define your data model once in `.storm` format and generate complete C# or PHP backend code with zero boilerplate.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Scaffold a new .NET project
python main.py --init --template dotnet-csharp --name MyApi

# Edit the generated schema.storm to define your data model

# Generate all source files
python main.py --generate
```

## Commands

| Command | Short | Description |
|---------|-------|-------------|
| `--init` | `-i` | Scaffold a new project with template |
| `--generate` | `-g` | Generate source code from `schema.storm` |
| `--template` | `-t` | Template to use (default: `dotnet-csharp`) |
| `--name` | `-n` | Project name (defaults to current directory) |

## Templates

| Template | Description |
|----------|-------------|
| `dotnet-csharp` | ASP.NET Core Web API with EF Core |
| `dotnet-csharp-clean-architecture` | Clean architecture: Domain, Application, Infrastructure, API |
| `laravel-php` | Laravel PHP with Composer |

## Schema Language (`.storm`)

Define enums and tables using a clean, readable syntax:

```storm
// Enums
enum Status {
    Active   = "active",
    Inactive = "inactive",
    Pending  = "pending"
}

// Tables
table User {
    id:       uuid pk;
    name:     string(min=2,max=100);
    email:    string(max=255) unique;
    role:     Role;
    status:   Status;
    createdAt:datetime;
}

table Product {
    id:      int? pk;
    name:    string(min=1,max=200);
    price:   double(min=0) = 0;
    stock:   int(min=0) = 0;
    owner:   User;              // foreign key
    createdAt:datetime;
}
```

### Type System

| Type | C# | Notes |
|------|-----|-------|
| `int` | `int` | Supports `pk`, `unique`, `min`, `max` |
| `long` | `long` | |
| `float` | `float` | |
| `double` | `double` | |
| `string` | `string` | Supports `min`, `max`, `length` |
| `bool` | `bool` | |
| `uuid` | `Guid` | |
| `datetime` | `DateTime` | |

- Append `?` for nullable: `int?`, `uuid?`
- Reference other tables as foreign keys: `owner:User`
- Reference enums: `status:Status`
- Default values with expressions: `price:double = 0`, `qty:int = 5 * 4`

### Expressions

Constant expressions in default values are evaluated at parse time:

| Expression | Result |
|------------|--------|
| `5 * 4` | `20` |
| `(1 + 2) * 3` | `9` |
| `-5` | `-5` |
| `!true` | `false` |

## Generated Artifacts (C#)

For each table, `--generate` produces:

| File | Path | Description |
|------|------|-------------|
| `{Entity}.cs` | `Models/` | Entity class with properties |
| `{Entity}RequestDto.cs` | `Dtos/` | Create/update payload |
| `{Entity}ResponseDto.cs` | `Dtos/` | Full response |
| `{Entity}ResponseSimplifiedDto.cs` | `Dtos/` | Lightweight response (circular ref safe) |
| `I{Entity}Service.cs` | `IServices/` | Service interface |
| `{Entity}Service.cs` | `Services/` | EF Core + AutoMapper implementation |
| `{Entity}Controller.cs` | `Controllers/` | REST API with Swagger annotations |
| `{Entity}MappingProfile.cs` | `Mappers/` | AutoMapper profile |

Shared base files generated once:
- `IGenericService.cs` — generic CRUD interface
- `GenericService.cs` — generic EF Core implementation
- `GenericController.cs` — generic REST controller
- `PaginatedResult.cs` — pagination model + `IQueryable` extension

## Project Structure

```
src/
  ast.py              AST node types and factory methods
  column.py           Column type definitions
  enum.py             Enum AST node handler
  error_handler.py    Formatted error reporting with context
  interpreter.py      Schema interpreter, dependency graph, code generator
  keyword.py          Language keywords
  parser.py           Recursive descent parser
  table.py            Table AST node handler
  template.py         Template enum definitions
  tokenizer.py         Tokenizer/lexer
  tok_type.py         Token type enum
  generic_*.py        C# template strings (controller, service, mapper, pagination)

tests/
  test_parser.py          Parser tests (33)
  test_tokenizer.py       Tokenizer tests (26)
  test_error_handler.py   Error handler tests (5)
  test_integration.py     Integration tests (7)
```

## NuGet Packages (C#)

Installed automatically during `--init`:

- Microsoft.EntityFrameworkCore
- Microsoft.EntityFrameworkCore.SqlServer
- Microsoft.EntityFrameworkCore.Design
- Microsoft.AspNetCore.Identity.EntityFrameworkCore
- AutoMapper
- Newtonsoft.Json
- Scrutor
- Swashbuckle.AspNetCore
- Scalar.AspNetCore

## Requirements

- Python 3.10+
- **dotnet-csharp**: .NET SDK 8+, EF Core global tool
- **dotnet-csharp-clean-architecture**: .NET SDK 8+, EF Core global tool
- **laravel-php**: PHP 12+, Composer
