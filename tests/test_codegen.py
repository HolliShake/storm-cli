"""
Comprehensive tests for all three template types:
  - dotnet-csharp
  - dotnet-csharp-clean-architecture
  - laravel-php

Each test writes a schema + config into a temporary directory, runs code
generation through Interpreter, then asserts that all expected files exist
and contain the expected patterns.
"""

import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.interpreter import Interpreter


# ────────────────────────────────────────────────────────────────────────
#  Shared test schema   (two tables + one enum → exercises FK, enum, PK)
# ────────────────────────────────────────────────────────────────────────
TEST_SCHEMA = """\
enum Category {
    Electronics = "electronics",
    Clothing    = "clothing",
    Food        = "food"
}

table User {
    id:    uuid pk;
    name:  string(min=2,max=100);
    email: string(max=255) unique;
    createdAt: datetime;
    updatedAt: datetime;
}

table Item {
    id:       int? pk;
    title:    string(min=1,max=200);
    price:    double(min=0) = 0;
    qty:      int(min=0) = 0;
    category: Category;
    ownerId:  uuid;
    owner:    User;
    createdAt: datetime;
    updatedAt: datetime;
}
"""


SIMPLE_SCHEMA = """\
enum Status {
    Active   = "active",
    Inactive = "inactive"
}

table Widget {
    id:    int? pk;
    label: string(min=1,max=100);
    status: Status;
}
"""


# ────────────────────────────────────────────────────────────────────────
#  Configs for each template
# ────────────────────────────────────────────────────────────────────────
DOTNET_CONFIG = {
    "EnumPath": "./Static",
    "ModelPath": "./Models",
    "ControllerPath": "./Controllers",
    "DtoPath": "./Dtos",
    "IServicePath": "./IServices",
    "ServicePath": "./Services",
    "MapperPath": "./Mappers",
    "DbContextPath": "./Data",
}

CLEAN_ARCH_CONFIG = {
    "EnumPath": "./DOMAIN/Static",
    "ModelPath": "./DOMAIN/Models",
    "ControllerPath": "./API/Controllers",
    "DtoPath": "./APPLICATION/Dtos",
    "IServicesPath": "./APPLICATION/IServices",
    "ServicePath": "./INFRASTRUCTURE/Services",
    "MapperPath": "./INFRASTRUCTURE/Mappers",
    "DbContextPath": "./INFRASTRUCTURE/Data",
}

LARAVEL_CONFIG = {
    "EnumPath": "./app/Static",
    "ModelPath": "./app/Models",
    "ControllerPath": "./app/Controllers",
    "DtoPath": "./app/Dtos",
    "IServicePath": "./app/IServices",
    "ServicePath": "./app/Services",
    "MapperPath": "./app/Mappers",
    "MigrationsPath": "./database/migrations",
}


# ────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────

def _write_schema(schema_dir: str, schema_content: str) -> str:
    """Write schema.storm into schema_dir, return path."""
    path = os.path.join(schema_dir, "schema.storm")
    with open(path, "w", encoding="utf-8") as f:
        f.write(schema_content)
    return path


def _read_file(base: str, rel_path: str) -> str:
    """Read a file relative to base dir, return its content."""
    full = os.path.join(base, rel_path.lstrip("./"))
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _assert_file_exists(base: str, rel_path: str):
    full = os.path.join(base, rel_path.lstrip("./"))
    assert os.path.isfile(full), f"Expected file missing: {rel_path}"
    return _read_file(base, rel_path)


def _assert_file_contains(base: str, rel_path: str, *needles: str):
    content = _assert_file_exists(base, rel_path)
    for needle in needles:
        assert needle in content, (
            f"Expected '{needle}' not found in {rel_path}"
        )


def _assert_file_not_contains(base: str, rel_path: str, *needles: str):
    content = _assert_file_exists(base, rel_path)
    for needle in needles:
        assert needle not in content, (
            f"Unexpected '{needle}' found in {rel_path}"
        )


# ────────────────────────────────────────────────────────────────────────
#  DOTNET CSHARP (simple)
# ────────────────────────────────────────────────────────────────────────

class TestDotnetCSharp:
    """Tests for the dotnet-csharp template."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        schema_path = _write_schema(str(tmp_path), TEST_SCHEMA)
        self.interp = Interpreter(schema_path)
        self.interp.generate(DOTNET_CONFIG, "TestApp", str(tmp_path))

    # ── directory structure ──────────────────────────────────────────

    def test_dirs_exist(self):
        for rel in ["./Static", "./Models", "./Controllers", "./Dtos",
                     "./IServices", "./Services", "./Mappers", "./Data"]:
            full = os.path.join(str(self.tmp), rel.lstrip("./"))
            assert os.path.isdir(full), f"Missing dir: {rel}"

    # ── base generic files ───────────────────────────────────────────

    def test_generic_files(self):
        _assert_file_exists(str(self.tmp), "./IServices/IGenericService.cs")
        _assert_file_exists(str(self.tmp), "./Services/GenericService.cs")
        _assert_file_exists(str(self.tmp), "./Controllers/GenericController.cs")
        _assert_file_exists(str(self.tmp), "./Dtos/Shared/PaginatedResult.cs")
        _assert_file_exists(str(self.tmp), "./Dtos/Shared/PaginateQuery.cs")

    def test_program_cs(self):
        _assert_file_contains(str(self.tmp), "./Program.cs",
            "TestApp", "AddDbContext", "AddIdentity", "MapControllers")

    def test_db_context(self):
        _assert_file_contains(str(self.tmp), "./Data/AppDbContext.cs",
            "IdentityDbContext", "public DbSet<Item> Items")

    # ── enum ─────────────────────────────────────────────────────────

    def test_enum_generated(self):
        _assert_file_contains(str(self.tmp), "./Static/Category.cs",
            "public enum Category", "Electronics", "Clothing", "Food")

    # ── User model (IdentityUser) ────────────────────────────────────

    def test_user_model_is_identity(self):
        _assert_file_contains(str(self.tmp), "./Models/User.cs",
            "IdentityUser<Guid>")

    def test_user_model_skips_identity_fields(self):
        content = _read_file(str(self.tmp), "./Models/User.cs")
        assert "public Guid Id" not in content
        assert "public string UserName" not in content

    def test_user_model_has_custom_fields(self):
        # Email is provided by IdentityUser so it is skipped
        _assert_file_contains(str(self.tmp), "./Models/User.cs",
            "public string Name")
        _assert_file_not_contains(str(self.tmp), "./Models/User.cs",
            "public string Email")

    # ── Item model ───────────────────────────────────────────────────

    def test_item_model_has_fk(self):
        _assert_file_contains(str(self.tmp), "./Models/Item.cs",
            "public Guid OwnerId", "public User? Owner")

    def test_item_model_has_enum(self):
        _assert_file_contains(str(self.tmp), "./Models/Item.cs",
            "public Category Category")

    # ── Item DTOs ────────────────────────────────────────────────────

    def test_item_request_dto(self):
        _assert_file_contains(str(self.tmp), "./Dtos/ItemDto/ItemRequestDto.cs",
            "ItemRequestDto", "public string Title", "public Category Category")

    def test_item_response_dto(self):
        _assert_file_contains(str(self.tmp), "./Dtos/ItemDto/ItemResponseDto.cs",
            "ItemResponseDto", "public int? Id", "public string Title")

    def test_item_simplified_dto(self):
        _assert_file_contains(str(self.tmp), "./Dtos/ItemDto/ItemResponseSimplifiedDto.cs",
            "ItemResponseSimplifiedDto", "public int Id", "public string Title")

    # ── Item service / controller ────────────────────────────────────

    def test_item_iservice(self):
        _assert_file_contains(str(self.tmp), "./IServices/IItemService.cs",
            "IItemService", "IGenericService<Item")

    def test_item_service(self):
        _assert_file_contains(str(self.tmp), "./Services/ItemService.cs",
            "ItemService", "GenericService<Item", "PaginateByOwnerAsync")

    def test_item_controller(self):
        _assert_file_contains(str(self.tmp), "./Controllers/ItemController.cs",
            "ItemController", "GenericController<Item", "Show", "Index", "Store")

    # ── Item mapper ──────────────────────────────────────────────────

    def test_item_mapper(self):
        _assert_file_contains(str(self.tmp), "./Mappers/ItemMappingProfile.cs",
            "ItemMappingProfile", "Item", "ItemRequestDto")

    # ── User service / controller (no FK) ────────────────────────────

    def test_user_iservice_no_fk(self):
        _assert_file_contains(str(self.tmp), "./IServices/IUserService.cs",
            "IUserService", "IGenericService<User")

    def test_user_controller(self):
        _assert_file_contains(str(self.tmp), "./Controllers/UserController.cs",
            "UserController", "GenericController<User")


# ────────────────────────────────────────────────────────────────────────
#  DOTNET CSHARP CLEAN ARCHITECTURE
# ────────────────────────────────────────────────────────────────────────

class TestDotnetCleanArchitecture:
    """Tests for the dotnet-csharp-clean-architecture template."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        schema_path = _write_schema(str(tmp_path), TEST_SCHEMA)
        self.interp = Interpreter(schema_path)
        self.interp.generate(CLEAN_ARCH_CONFIG, "CleanApp", str(tmp_path))

    # ── directory structure ──────────────────────────────────────────

    def test_layer_dirs_exist(self):
        for layer in ["DOMAIN", "APPLICATION", "INFRASTRUCTURE", "API"]:
            full = os.path.join(str(self.tmp), layer)
            assert os.path.isdir(full), f"Missing layer dir: {layer}"

    def test_sub_dirs_exist(self):
        for rel in ["DOMAIN/Static", "DOMAIN/Models", "API/Controllers",
                     "APPLICATION/Dtos", "APPLICATION/IServices",
                     "INFRASTRUCTURE/Services", "INFRASTRUCTURE/Mappers",
                     "INFRASTRUCTURE/Data"]:
            full = os.path.join(str(self.tmp), rel)
            assert os.path.isdir(full), f"Missing dir: {rel}"

    # ── program.cs in API layer ──────────────────────────────────────

    def test_program_cs_in_api(self):
        _assert_file_contains(str(self.tmp), "./API/Program.cs",
            "CleanApp", "DOMAIN.Models", "INFRASTRUCTURE.Data")

    # ── model namespace references domain ────────────────────────────

    def test_user_model_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./DOMAIN/Models/User.cs",
            "DOMAIN.Models", "IdentityUser<Guid>")

    def test_item_model_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./DOMAIN/Models/Item.cs",
            "DOMAIN.Models")

    # ── DTOs in APPLICATION ──────────────────────────────────────────

    def test_dto_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./APPLICATION/Dtos/ItemDto/ItemRequestDto.cs",
            "APPLICATION.Dtos.ItemDto")

    # ── iservice in APPLICATION ──────────────────────────────────────

    def test_iservice_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./APPLICATION/IServices/IItemService.cs",
            "APPLICATION.IServices")

    # ── service + mapper in INFRASTRUCTURE ───────────────────────────

    def test_service_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./INFRASTRUCTURE/Services/ItemService.cs",
            "INFRASTRUCTURE.Services")

    def test_mapper_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./INFRASTRUCTURE/Mappers/ItemMappingProfile.cs",
            "INFRASTRUCTURE.Mappers")

    # ── controller in API ────────────────────────────────────────────

    def test_controller_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./API/Controllers/ItemController.cs",
            "API.Controllers")

    # ── dbcontext in INFRASTRUCTURE ──────────────────────────────────

    def test_dbcontext_clean_ns(self):
        _assert_file_contains(str(self.tmp), "./INFRASTRUCTURE/Data/AppDbContext.cs",
            "INFRASTRUCTURE.Data")

    # ── cross-cutting ────────────────────────────────────────────────

    def test_clean_arch_all_expected_files(self):
        """Smoke test: every table gets its full set of files."""
        for name in ["User", "Item"]:
            _assert_file_exists(str(self.tmp), f"./DOMAIN/Models/{name}.cs")
            _assert_file_exists(str(self.tmp), f"./APPLICATION/Dtos/{name}Dto/{name}RequestDto.cs")
            _assert_file_exists(str(self.tmp), f"./APPLICATION/Dtos/{name}Dto/{name}ResponseDto.cs")
            _assert_file_exists(str(self.tmp), f"./APPLICATION/Dtos/{name}Dto/{name}ResponseSimplifiedDto.cs")
            _assert_file_exists(str(self.tmp), f"./APPLICATION/IServices/I{name}Service.cs")
            _assert_file_exists(str(self.tmp), f"./INFRASTRUCTURE/Services/{name}Service.cs")
            _assert_file_exists(str(self.tmp), f"./INFRASTRUCTURE/Mappers/{name}MappingProfile.cs")
            _assert_file_exists(str(self.tmp), f"./API/Controllers/{name}Controller.cs")

    def test_clean_arch_enum(self):
        _assert_file_contains(str(self.tmp), "./DOMAIN/Static/Category.cs",
            "enum Category", "Electronics")


# ────────────────────────────────────────────────────────────────────────
#  LARAVEL PHP
# ────────────────────────────────────────────────────────────────────────

class TestLaravelPhp:
    """Tests for the laravel-php template."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        schema_path = _write_schema(str(tmp_path), TEST_SCHEMA)
        self.interp = Interpreter(schema_path)
        self.interp.generate(LARAVEL_CONFIG, "LaravelApp", str(tmp_path))

    # ── directory structure ──────────────────────────────────────────

    def test_dirs_exist(self):
        for rel in ["./app/Static", "./app/Models", "./app/Controllers",
                     "./app/Services", "./database/migrations", "./routes"]:
            full = os.path.join(str(self.tmp), rel.lstrip("./"))
            assert os.path.isdir(full), f"Missing dir: {rel}"

    # ── base controller ──────────────────────────────────────────────

    def test_base_controller(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/Controller.php",
            "class Controller", "function ok", "function notFound")

    def test_base_controller_oa_schemas(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/Controller.php",
            "UnauthenticatedResponse", "ForbiddenResponse",
            "ValidationErrorResponse", "InternalServerErrorResponse")

    # ── enum ─────────────────────────────────────────────────────────

    def test_enum_generated(self):
        _assert_file_contains(str(self.tmp), "./app/Static/Category.php",
            "enum Category: string", 'Electronics = "electronics"',
            'Clothing = "clothing"', 'Food = "food"')

    def test_enum_has_oa_schema(self):
        _assert_file_contains(str(self.tmp), "./app/Static/Category.php",
            '#[OA\\Schema(', 'enum: Category::class')

    # ── User model ───────────────────────────────────────────────────

    def test_user_model_php_tag(self):
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "<?php", "namespace App\\Models;")

    def test_user_model_extends_model(self):
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "class User extends Model")

    def test_user_model_table_name(self):
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "$table = 'user'")

    def test_user_model_fillable(self):
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "$fillable = [", "'name'", "'email'")

    def test_user_model_casts(self):
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "casts()", "'created_at' => 'datetime'")

    def test_user_model_has_oa_schemas(self):
        content = _read_file(str(self.tmp), "./app/Models/User.php")
        assert 'schema: "User"' in content
        assert 'schema: "PaginatedUser"' in content
        assert 'schema: "GetUserResponse200"' in content
        assert 'schema: "CreateUserResponse200"' in content
        assert 'schema: "UpdateUserResponse200"' in content
        assert 'schema: "DeleteUserResponse200"' in content

    def test_user_has_many_items(self):
        """User should have a HasMany relationship to Items."""
        _assert_file_contains(str(self.tmp), "./app/Models/User.php",
            "function items()", "HasMany", "Item::class", "'owner_id'")

    # ── Item model ───────────────────────────────────────────────────

    def test_item_model_exists(self):
        _assert_file_exists(str(self.tmp), "./app/Models/Item.php")

    def test_item_model_fk_relation(self):
        _assert_file_contains(str(self.tmp), "./app/Models/Item.php",
            "function owner()", "BelongsTo", "User::class", "'owner_id'")

    def test_item_model_enum_cast(self):
        _assert_file_contains(str(self.tmp), "./app/Models/Item.php",
            "'category' => Category::class")

    def test_item_model_fillable_no_dup_fk(self):
        content = _read_file(str(self.tmp), "./app/Models/Item.php")
        # owner_id appears once in the OA schema + once in fillable = OK (total count 2)
        # But it should NOT appear twice within the fillable array itself
        fillable_part = content.split("$fillable")[1].split("];")[0]
        assert fillable_part.count("'owner_id'") <= 1, (
            f"owner_id duplicated in fillable: {fillable_part}"
        )
        # owner FK field should not be directly in fillable
        assert "'owner'" not in fillable_part, (
            f"'owner' found in fillable: {fillable_part}"
        )

    def test_item_model_oa_relation_property(self):
        _assert_file_contains(str(self.tmp), "./app/Models/Item.php",
            '#/components/schemas/User')

    # ── Controller ───────────────────────────────────────────────────

    def test_item_controller_oa_routes(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/ItemController.php",
            '#[OA\\Get(', '#[OA\\Post(', '#[OA\\Put(', '#[OA\\Delete(')

    def test_item_controller_filter_param(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/ItemController.php",
            'filter[owner_id]', 'Filter by User ID')

    def test_item_controller_methods(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/ItemController.php",
            "function index", "function show", "function store",
            "function update", "function destroy")

    def test_user_controller_no_filter_param(self):
        """User has no FK fields, so no filter params."""
        content = _read_file(str(self.tmp), "./app/Controllers/UserController.php")
        assert "filter[" not in content

    def test_controller_response_schemas(self):
        _assert_file_contains(str(self.tmp), "./app/Controllers/ItemController.php",
            "PaginatedItemResponse200", "GetItemResponse200",
            "UnauthenticatedResponse", "ForbiddenResponse",
            "ValidationErrorResponse")

    # ── Service ──────────────────────────────────────────────────────

    def test_item_service_class(self):
        _assert_file_contains(str(self.tmp), "./app/Services/ItemService.php",
            "class ItemService", "function paginate", "function getById",
            "function create", "function update", "function delete")

    def test_item_service_filterable(self):
        _assert_file_contains(str(self.tmp), "./app/Services/ItemService.php",
            "filterable", "'owner_id'")

    def test_item_service_rules(self):
        _assert_file_contains(str(self.tmp), "./app/Services/ItemService.php",
            "function rules", "'title'", "'price'", "'category'")

    # ── Migrations ───────────────────────────────────────────────────

    def test_user_migration_exists(self):
        files = os.listdir(os.path.join(str(self.tmp), "database/migrations"))
        user_mig = [f for f in files if "users" in f]
        assert len(user_mig) == 1, f"Expected 1 users migration, got: {files}"

    def test_item_migration_exists(self):
        files = os.listdir(os.path.join(str(self.tmp), "database/migrations"))
        item_mig = [f for f in files if "items" in f]
        assert len(item_mig) == 1, f"Expected 1 items migration, got: {files}"

    def test_item_migration_content(self):
        files = os.listdir(os.path.join(str(self.tmp), "database/migrations"))
        item_mig = [f for f in files if "items" in f][0]
        _assert_file_contains(str(self.tmp), f"./database/migrations/{item_mig}",
            "Schema::create('items'", "foreignId('owner_id')",
            "$table->string('title'", "$table->double('price'")

    # ── Routes ───────────────────────────────────────────────────────

    def test_routes_generated(self):
        _assert_file_contains(str(self.tmp), "./routes/api.php",
            "Route::prefix('api')",
            "UserController::class",
            "ItemController::class",
            "'index'", "'store'", "'update'", "'destroy'")

    def test_route_count(self):
        content = _read_file(str(self.tmp), "./routes/api.php")
        # 2 tables × 5 = 10, + 1 prefix + 1 FK + 1 enum = 13
        assert content.count("Route::") == 13


# ────────────────────────────────────────────────────────────────────────
#  EDGE CASES
# ────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests covering edge-case scenarios."""

    def test_simple_schema_dotnet(self, tmp_path):
        """Single table, no FK, single enum → everything still works."""
        schema_path = _write_schema(str(tmp_path), SIMPLE_SCHEMA)
        interp = Interpreter(schema_path)
        interp.generate(DOTNET_CONFIG, "SimpleApp", str(tmp_path))

        # Verify minimal set
        _assert_file_exists(str(tmp_path), "./Static/Status.cs")
        _assert_file_exists(str(tmp_path), "./Models/Widget.cs")
        _assert_file_exists(str(tmp_path), "./Controllers/WidgetController.cs")
        # No FK, but enum → PaginateByStatusAsync exists
        content = _read_file(str(tmp_path), "./Services/WidgetService.cs")
        assert "PaginateByStatusAsync" in content
        assert "PaginateBy" not in content.replace("PaginateByStatusAsync", "")

    def test_simple_schema_laravel(self, tmp_path):
        """Single table, no FK, single enum → Laravel gen works."""
        schema_path = _write_schema(str(tmp_path), SIMPLE_SCHEMA)
        interp = Interpreter(schema_path)
        interp.generate(LARAVEL_CONFIG, "SimpleLaravel", str(tmp_path))

        _assert_file_exists(str(tmp_path), "./app/Static/Status.php")
        _assert_file_exists(str(tmp_path), "./app/Models/Widget.php")
        _assert_file_exists(str(tmp_path), "./app/Controllers/WidgetController.php")
        # No FK → no filter params in controller
        content = _read_file(str(tmp_path), "./app/Controllers/WidgetController.php")
        assert "filter[" not in content

    def test_table_without_pk(self, tmp_path):
        """Table with no pk field → defaults to int Id."""
        schema = "table NoPk { label: string; }"
        schema_path = _write_schema(str(tmp_path), schema)
        interp = Interpreter(schema_path)
        # Should not crash
        interp.generate(DOTNET_CONFIG, "NoPkApp", str(tmp_path))
        _assert_file_exists(str(tmp_path), "./Models/NoPk.cs")

    def test_enum_no_values(self, tmp_path):
        """Enum with items that have no string values."""
        schema = "enum Bare { A B C }"
        schema_path = _write_schema(str(tmp_path), schema)
        interp = Interpreter(schema_path)
        interp.generate(LARAVEL_CONFIG, "BareApp", str(tmp_path))
        content = _read_file(str(tmp_path), "./app/Static/Bare.php")
        assert "case A" in content
        assert "case B" in content

    def test_topological_order(self, tmp_path):
        """Tables are emitted in dependency order (User before Item)."""
        schema_path = _write_schema(str(tmp_path), TEST_SCHEMA)
        interp = Interpreter(schema_path)
        order = interp.get_table_order()
        assert order.index("User") < order.index("Item"), (
            "User must come before Item in topological sort"
        )

    def test_snake_case_conversion(self, tmp_path):
        schema = "table TestTable { id: int pk; createdAt: datetime; }"
        schema_path = _write_schema(str(tmp_path), schema)
        interp = Interpreter(schema_path)
        assert interp._snake_case("TestTable") == "test_table"
        assert interp._snake_case("createdAt") == "created_at"

    def test_pascal_case_conversion(self, tmp_path):
        schema = "table X { id: int pk; }"
        schema_path = _write_schema(str(tmp_path), schema)
        interp = Interpreter(schema_path)
        assert interp._pascal_case("test_table") == "Test_table"
        assert interp._pascal_case("foo") == "Foo"

    def test_all_three_templates_idempotent(self, tmp_path):
        """Running generate twice should not crash (idempotency)."""
        schema_path = _write_schema(str(tmp_path), SIMPLE_SCHEMA)

        for config in [DOTNET_CONFIG, CLEAN_ARCH_CONFIG, LARAVEL_CONFIG]:
            tmp = str(tmp_path / config.get("EnumPath", ".").split("/")[0])
            os.makedirs(tmp, exist_ok=True)

            interp = Interpreter(schema_path)
            interp.generate(config, "App", str(tmp_path))
            # Second run — should not crash
            interp2 = Interpreter(schema_path)
            interp2.generate(config, "App", str(tmp_path))
