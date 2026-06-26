




from collections import deque
import os

from src.ast import AstType
from src.enum import Enum
from src.error_handler import raise_error
from src.generic_controller_csharp import GENERIC_CONTROLLER_CSHARP, GENERIC_CONTROLLER_TEMPLATE_CSHARP
from src.generic_mapper_csharp import GENERIC_MAPPER_TEMPLATE_CSHARP
from src.generic_pagination_csharp import GENERIC_PAGINATION_CSHARP
from src.generic_query_chsarp import GENERIC_QUERY_CSHARP
from src.generic_service_csharp import GENERIC_ISERVICE_CSHARP, GENERIC_SERVICE_CSHARP
from src.parser import Parser
from src.table import Table


class Interpreter(Parser):
    def __init__(self, filename):
        super().__init__(filename)
        ast = self.parse()
        self.tables = {}
        self.enums = {}
        self.deps = {}
        self._ordered = []
        self._collect(ast)

    def _collect(self, ast):
        cur = ast.next
        while cur:
            if cur.node_type == AstType.TABLE_DECL:
                name = cur.a.value
                self.tables[name] = cur
            elif cur.node_type == AstType.ENUM_DECL:
                name = cur.a.value
                self.enums[name] = cur
            cur = cur.next

        table_names = set(self.tables.keys())

        for name, table_node in self.tables.items():
            deps = set()
            field = table_node.b
            while field:
                type_node = field.b
                type_name = type_node.value.rstrip('?')
                if type_name in table_names and type_name != name:
                    deps.add(type_name)
                field = field.next
            self.deps[name] = deps

        self._ordered = self._topological_sort()

    def _topological_sort(self):
        indegree = {name: 0 for name in self.tables}
        for name, deps in self.deps.items():
            indegree[name] = len(deps)

        queue = deque(name for name, deg in indegree.items() if deg == 0)
        ordered = []

        while queue:
            current = queue.popleft()
            ordered.append(current)
            for name, deps in self.deps.items():
                if current in deps:
                    indegree[name] -= 1
                    if indegree[name] == 0:
                        queue.append(name)

        if len(ordered) != len(self.tables):
            remaining = set(self.tables.keys()) - set(ordered)
            ordered.extend(remaining)

        return ordered

    def _try_op(self, node, op_fn, zero_fn=None):
        try:
            return op_fn()
        except TypeError as e:
            raise_error(self.file_path, self.file_data, f"type error: {e}", node.position)
        except ZeroDivisionError:
            if zero_fn:
                return zero_fn()
            raise_error(self.file_path, self.file_data, "division by zero", node.position)

    def _evaluate_expression(self, node):
        if node is None:
            return None

        nt = node.node_type

        if nt == AstType.INT_LITERAL:
            return int(node.value)
        if nt == AstType.STR_LITERAL:
            return node.value
        if nt == AstType.BOOL_LITERAL:
            return node.value == 'true'
        if nt == AstType.IDENTIFIER:
            return None

        l = self._evaluate_expression(node.a)
        r = self._evaluate_expression(node.b)

        if nt == AstType.BINARY_ADD:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l + r)
        if nt == AstType.BINARY_SUB:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l - r)
        if nt == AstType.BINARY_MUL:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l * r)
        if nt == AstType.BINARY_DIV:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l / r)
        if nt == AstType.BINARY_MOD:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l % r)

        if nt == AstType.UNARY_MINUS:
            if l is None:
                return None
            return self._try_op(node, lambda: -l)
        if nt == AstType.UNARY_PLUS:
            if l is None:
                return None
            return self._try_op(node, lambda: +l)
        if nt == AstType.UNARY_NOT:
            if l is None:
                return None
            return self._try_op(node, lambda: not l)
        if nt == AstType.UNARY_BITWISE_NOT:
            if l is None:
                return None
            return self._try_op(node, lambda: ~l)

        if nt == AstType.BINARY_EQ:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l == r)
        if nt == AstType.BINARY_NE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l != r)
        if nt == AstType.BINARY_LT:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l < r)
        if nt == AstType.BINARY_LTE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l <= r)
        if nt == AstType.BINARY_GT:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l > r)
        if nt == AstType.BINARY_GTE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l >= r)

        if nt == AstType.BINARY_SHL:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l << r)
        if nt == AstType.BINARY_SHR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l >> r)
        if nt == AstType.BINARY_BITWISE_AND:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l & r)
        if nt == AstType.BINARY_BITWISE_XOR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l ^ r)
        if nt == AstType.BINARY_BITWISE_OR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l | r)

        if nt == AstType.BINARY_LOGICAL_AND:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l and r)
        if nt == AstType.BINARY_LOGICAL_OR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l or r)

        return None

    def get_tables(self):
        table_names = set(self.tables.keys())
        result = []
        for name in self._ordered:
            node = self.tables[name]
            table = Table.from_ast(node, table_names)
            for _, ct in table.columns:
                if ct.default_value_node is not None:
                    ct.default_value = self._evaluate_expression(ct.default_value_node)
            result.append(table)
        return result

    def get_enums(self):
        return [Enum.from_ast(node) for node in self.enums.values()]

    def get_table_order(self):
        return list(self._ordered)

    # ── code generation ──────────────────────────────────────────────

    STORM_TO_CSHARP = {
        "int": "int", "long": "long", "float": "float", "double": "double",
        "string": "string", "bool": "bool", "uuid": "Guid", "datetime": "DateTime",
    }

    CSHARP_TO_ROUTE_CONSTRAINT = {
        "int": "int", "long": "long", "float": "float", "double": "double",
        "bool": "bool", "Guid": "guid", "DateTime": "datetime",
    }

    def _path_to_namespace(self, path, project_name):
        cleaned = path.lstrip("./").replace("/", ".").replace("\\", ".")
        return f"{project_name}.{cleaned}" if cleaned else project_name

    def _get_pk_field(self, table_node):
        f = table_node.b
        while f:
            if f.value == "pk":
                return f
            f = f.next
        return None

    def _get_fk_columns(self, table_node):
        """Return list of (field_name, ref_table, ref_pk_type) for FK columns."""
        fks = []
        table_names = set(self.tables.keys())
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip('?')
            if type_name in table_names:
                field_name = self._pascal_case(f.a.value)
                ref_pk_type = self._get_pk_type(self.tables[type_name])
                fks.append((field_name, type_name, ref_pk_type))
            f = f.next
        return fks

    def _get_pk_type(self, table_node):
        pk = self._get_pk_field(table_node)
        if pk is None:
            return "int"
        type_name = pk.b.value.rstrip("?")
        return self.STORM_TO_CSHARP.get(type_name, "int")

    def _field_csharp_type(self, field_node):
        type_node = field_node.b
        type_name = type_node.value.rstrip("?")
        is_nullable = type_node.value.endswith("?")

        mapped = self.STORM_TO_CSHARP.get(type_name)
        if mapped:
            if mapped == "string":
                return mapped
            return f"{mapped}?" if is_nullable else mapped

        if type_name in self.tables:
            ref_pk_type = self._get_pk_type(self.tables[type_name])
            return (ref_pk_type, type_name)

        if type_name in self.enums:
            enum_name = self._pascal_case(type_name)
            return f"{enum_name}?" if is_nullable else enum_name

        return "object"

    @staticmethod
    def _pascal_case(name):
        if not name:
            return name
        return name[0].upper() + name[1:]

    def _build_namespaces(self, config, project_name):
        ns = {}
        for key, path in config.items():
            ns[key] = self._path_to_namespace(path, project_name)
        return ns

    def _substitute_template(self, template, vars_dict):
        result = template
        for key, value in vars_dict.items():
            result = result.replace("$$" + key + "$$", value)
        return result

    # ── model ────────────────────────────────────────────────────────

    def _table_uses_enums(self, table_node):
        """Return set of enum names referenced by fields in this table."""
        used = set()
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.enums:
                used.add(type_name)
            f = f.next
        return used

    # Properties already provided by IdentityUser / IdentityUser<TKey>
    _IDENTITY_USER_FIELDS = {
        "Id", "UserName", "NormalizedUserName", "Email", "NormalizedEmail",
        "EmailConfirmed", "PasswordHash", "SecurityStamp", "ConcurrencyStamp",
        "PhoneNumber", "PhoneNumberConfirmed", "TwoFactorEnabled",
        "LockoutEnd", "LockoutEnabled", "AccessFailedCount",
    }

    def _generate_model(self, table_node, namespace, enum_ns=""):
        name = table_node.a.value
        pk = self._get_pk_field(table_node)
        pk_name = self._pascal_case(pk.a.value) if pk else "Id"

        is_user = (name == "User")
        identity_base = ""
        usings = ""
        identity_skip_fields = set()

        if is_user:
            # Require PK type to be uuid
            pk_type_storm = pk.b.value.rstrip("?")
            if pk_type_storm != "uuid":
                raise_error(
                    self.file_path, self.file_data,
                    f"User table primary key must be 'uuid', got '{pk_type_storm}'",
                    pk.position,
                )
            identity_base = " : IdentityUser<Guid>"
            usings += "using Microsoft.AspNetCore.Identity;\n"
            identity_skip_fields = self._IDENTITY_USER_FIELDS

        if enum_ns and self._table_uses_enums(table_node):
            usings += f"using {enum_ns};\n"

        if usings:
            usings += "\n"

        # collect all field names first to detect FK-id collisions
        all_names = set()
        f = table_node.b
        while f:
            all_names.add(self._pascal_case(f.a.value))
            f = f.next

        buf = [usings + f"namespace {namespace};", "", f"public class {name}{identity_base}", "{"]

        f = table_node.b
        while f:
            field_name = self._pascal_case(f.a.value)
            cs_type = self._field_csharp_type(f)

            # skip fields already provided by IdentityUser
            if is_user and field_name in identity_skip_fields:
                f = f.next
                continue

            if isinstance(cs_type, tuple):
                ref_pk_type, ref_name = cs_type
                fk_name = f"{field_name}Id"
                if fk_name not in all_names and fk_name not in identity_skip_fields:
                    buf.append(f"    public {ref_pk_type} {fk_name} {{ get; set; }}")
                buf.append(f"    public {ref_name}? {field_name} {{ get; set; }}")
            else:
                buf.append(f"    public {cs_type} {field_name} {{ get; set; }}")

            f = f.next

        buf.append("}")
        return "\n".join(buf)

    # ── dto ──────────────────────────────────────────────────────────

    def _generate_request_dto(self, table_node, namespace, enum_ns=""):
        name = table_node.a.value
        pk = self._get_pk_field(table_node)
        pk_name = self._pascal_case(pk.a.value) if pk else "Id"
        dto_name = f"{name}RequestDto"

        usings = ""
        if enum_ns and self._table_uses_enums(table_node):
            usings = f"using {enum_ns};\n\n"

        # collect field names to detect FK-id collisions
        all_names = set()
        fn = table_node.b
        while fn:
            all_names.add(self._pascal_case(fn.a.value))
            fn = fn.next

        buf = [usings + f"namespace {namespace};", "", f"public class {dto_name}", "{"]

        f = table_node.b
        while f:
            field_name = self._pascal_case(f.a.value)
            if field_name == pk_name:
                f = f.next
                continue
            cs_type = self._field_csharp_type(f)
            if isinstance(cs_type, tuple):
                ref_pk_type, _ = cs_type
                fk_name = f"{field_name}Id"
                if fk_name not in all_names:
                    buf.append(f"    public {ref_pk_type} {fk_name} {{ get; set; }}")
            else:
                buf.append(f"    public {cs_type} {field_name} {{ get; set; }}")
            f = f.next

        buf.append("}")
        return "\n".join(buf)

    def _generate_response_dto(self, table_node, namespace, enum_ns=""):
        name = table_node.a.value
        dto_name = f"{name}ResponseDto"

        usings = ""
        if enum_ns and self._table_uses_enums(table_node):
            usings = f"using {enum_ns};\n\n"

        # collect field names to detect FK-id collisions
        all_names = set()
        fn = table_node.b
        while fn:
            all_names.add(self._pascal_case(fn.a.value))
            fn = fn.next

        buf = [usings + f"namespace {namespace};", "", f"public class {dto_name}", "{"]

        f = table_node.b
        while f:
            field_name = self._pascal_case(f.a.value)
            cs_type = self._field_csharp_type(f)
            if isinstance(cs_type, tuple):
                ref_pk_type, _ = cs_type
                fk_name = f"{field_name}Id"
                if fk_name not in all_names:
                    buf.append(f"    public {ref_pk_type} {fk_name} {{ get; set; }}")
            else:
                buf.append(f"    public {cs_type} {field_name} {{ get; set; }}")
            f = f.next

        buf.append("}")
        return "\n".join(buf)

    def _generate_response_simplified_dto(self, table_node, namespace, enum_ns=""):
        name = table_node.a.value
        pk = self._get_pk_field(table_node)
        pk_name = self._pascal_case(pk.a.value) if pk else "Id"
        pk_type = self.STORM_TO_CSHARP.get(pk.b.value.rstrip("?"), "int") if pk else "int"
        dto_name = f"{name}ResponseSimplifiedDto"

        usings = ""
        if enum_ns and self._table_uses_enums(table_node):
            usings = f"using {enum_ns};\n\n"

        buf = [usings + f"namespace {namespace};", "", f"public class {dto_name}", "{"]
        buf.append(f"    public {pk_type} {pk_name} {{ get; set; }}")

        for nf in ["Name", "Title", "Label"]:
            f = table_node.b
            while f:
                if self._pascal_case(f.a.value) == nf:
                    cs_type = self._field_csharp_type(f)
                    buf.append(f"    public {cs_type[0] if isinstance(cs_type, tuple) else cs_type} {nf} {{ get; set; }}")
                    break
                f = f.next

        buf.append("}")
        return "\n".join(buf)

    # ── enum ─────────────────────────────────────────────────────────

    def _generate_csharp_enum(self, enum_node, namespace):
        name = enum_node.a.value
        buf = [f"namespace {namespace};", "", f"public enum {name}", "{"]
        cur = enum_node.b
        while cur:
            value = cur.b.value if cur.b else ""
            comment = f" // \"{value}\"" if value else ""
            buf.append(f"    {cur.a.value},{comment}")
            cur = cur.next
        buf.append("}")
        return "\n".join(buf)

    # ── template generators ──────────────────────────────────────────

    def _generate_iservice(self, table_name, namespace, pk_type, iservice_ns, model_ns, dto_ns, pagination_ns):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        extra_methods = ""
        for fk_name, fk_table, fk_pk_type in fks:
            lower_fk = fk_name[0].lower() + fk_name[1:]
            extra_methods += f"\n    public Task<PaginatedResult<{table_name}ResponseDto>> PaginateBy{fk_name}Async({fk_pk_type} {lower_fk}Id, PaginateQuery query);"

        using_pagination = f"using {pagination_ns};\n" if fks else ""

        return f"""\
{using_pagination}using {iservice_ns};
using {model_ns};
using {dto_ns};

namespace {namespace};

public interface I{table_name}Service : IGenericService<{table_name}, {table_name}ResponseDto, {table_name}RequestDto, {pk_type}>
{{{extra_methods}
}}
"""

    def _generate_service(self, table_name, namespace, pk_type, service_ns, iservice_ns, model_ns, dto_ns, pagination_ns):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        extra_methods = ""
        for fk_name, fk_table, fk_pk_type in fks:
            lower_fk = fk_name[0].lower() + fk_name[1:]
            extra_methods += f"""
    public async Task<PaginatedResult<{table_name}ResponseDto>> PaginateBy{fk_name}Async({fk_pk_type} {lower_fk}Id, PaginateQuery query)
    {{
        var q = _table.Where(e => e.{fk_name}Id == {lower_fk}Id);
        return await q
            .ProjectTo<{table_name}ResponseDto>(_mapper.ConfigurationProvider)
            .PaginateAsync(query.Page, query.Rows);
    }}
"""

        using_pagination = f"using {pagination_ns};\n" if fks else ""

        return f"""\
{using_pagination}using {service_ns};
using {iservice_ns};
using {model_ns};
using {dto_ns};
using Microsoft.EntityFrameworkCore;
using AutoMapper;
using AutoMapper.QueryableExtensions;

namespace {namespace};

public class {table_name}Service : GenericService<{table_name}, {table_name}ResponseDto, {table_name}RequestDto, {pk_type}>, I{table_name}Service
{{
    public {table_name}Service(DbContext context, IMapper mapper) : base(context, mapper) {{ }}
{extra_methods}
}}
"""

    def _generate_controller(self, table_name, namespace, pk_type, controller_ns, iservice_ns, dto_ns, pagination_ns, model_ns):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        pk_route_constraint = self.CSHARP_TO_ROUTE_CONSTRAINT.get(pk_type, "")
        id_route = f"{{id:{pk_route_constraint}}}" if pk_route_constraint else "{id}"

        extra_endpoints = ""
        for fk_name, fk_table, fk_pk_type in fks:
            lower_fk = fk_name[0].lower() + fk_name[1:]
            route_constraint = self.CSHARP_TO_ROUTE_CONSTRAINT.get(fk_pk_type, "")
            typed_param = f"{{{lower_fk}Id}}" if not route_constraint else f"{{{lower_fk}Id:{route_constraint}}}"
            extra_endpoints += f"""
    [HttpGet("{fk_table.lower()}/{typed_param}", Name = "Get{table_name}By{fk_name}")]
    [Tags("{table_name}")]
    [EndpointSummary("Paginated list by {fk_table}")]
    [EndpointDescription("Returns a paginated list of {table_name} records filtered by {fk_table}")]
    [ProducesResponseType(typeof(PaginatedResult<{table_name}ResponseDto>), StatusCodes.Status200OK)]
    public virtual async Task<ActionResult<PaginatedResult<{table_name}ResponseDto>>> IndexBy{fk_name}([FromRoute] {fk_pk_type} {lower_fk}Id,
        [FromQuery] PaginateQuery query)
    {{
        var result = await ((I{table_name}Service)_service).PaginateBy{fk_name}Async({lower_fk}Id, query);
        return Ok(result);
    }}
"""

        return f"""\
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using {controller_ns};
using {iservice_ns};
using {dto_ns};
using {pagination_ns};
using {model_ns};

namespace {namespace};

[ApiController]
[Route("api/[controller]")]
public class {table_name}Controller : GenericController<{table_name}, {table_name}ResponseDto, {table_name}RequestDto, {pk_type}>
{{
    public {table_name}Controller(I{table_name}Service service) : base(service) {{ }}

    [HttpGet("{id_route}", Name = "Get{table_name}ById")]
    [Tags("{table_name}")]
    [EndpointSummary("Retrieve by id")]
    [EndpointDescription("Returns a single {table_name} record by its unique identifier")]
    [ProducesResponseType(typeof({table_name}ResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<{table_name}ResponseDto>> Show([FromRoute] {pk_type} id)
    {{
        var result = await _service.GetByIdAsync(id);
        return Ok(result);
    }}

    [HttpGet(Name = "Get{table_name}Paginated")]
    [Tags("{table_name}")]
    [EndpointSummary("Paginated list")]
    [EndpointDescription("Returns a paginated list of {table_name} records")]
    [ProducesResponseType(typeof(PaginatedResult<{table_name}ResponseDto>), StatusCodes.Status200OK)]
    public virtual async Task<ActionResult<PaginatedResult<{table_name}ResponseDto>>> Index([FromQuery] PaginateQuery query)
    {{
        var result = await _service.PaginateAsync(query);
        return Ok(result);
    }}
{extra_endpoints}
    [HttpPost(Name = "Create{table_name}")]
    [Tags("{table_name}")]
    [EndpointSummary("Create new")]
    [EndpointDescription("Creates a new {table_name} record from the provided payload")]
    [ProducesResponseType(typeof({table_name}ResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public virtual async Task<ActionResult<{table_name}ResponseDto>> Store([FromBody] {table_name}RequestDto item)
    {{
        var result = await _service.CreateAsync(item);
        return Ok(result);
    }}

    [HttpPut("{id_route}", Name = "Update{table_name}")]
    [Tags("{table_name}")]
    [EndpointSummary("Update by id")]
    [EndpointDescription("Updates an existing {table_name} record identified by its id with the provided payload")]
    [ProducesResponseType(typeof({table_name}ResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<{table_name}ResponseDto>> Update([FromRoute] {pk_type} id, [FromBody] {table_name}RequestDto item)
    {{
        var result = await _service.UpdateAsync(id, item);
        return Ok(result);
    }}

    [HttpDelete("{id_route}", Name = "Delete{table_name}")]
    [Tags("{table_name}")]
    [EndpointSummary("Delete by id")]
    [EndpointDescription("Deletes a {table_name} record by its unique identifier")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<IActionResult> Destroy([FromRoute] {pk_type} id)
    {{
        await _service.DeleteAsync(id);
        return NoContent();
    }}
}}
"""


    def _generate_mapper(self, table_name, namespace, model_ns, dto_ns):
        vars_dict = {
            "config_mapper_path": namespace,
            "config_model_path": model_ns,
            "config_dto_path": dto_ns,
            "Entity": table_name,
            "TRequestDto": f"{table_name}RequestDto",
            "TResponseDto": f"{table_name}ResponseDto",
            "TResponseDtoSimplified": f"{table_name}ResponseSimplifiedDto",
        }
        return self._substitute_template(GENERIC_MAPPER_TEMPLATE_CSHARP, vars_dict)

    # ── dbcontext ───────────────────────────────────────────────────

    def _generate_appdbcontext(self, namespace, model_ns):
        usings = f"""\
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using {model_ns};
"""
        buf = [usings, f"namespace {namespace};", "", "public class AppDbContext : IdentityDbContext", "{"]
        buf.append("    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }")
        buf.append("")

        for name in self._ordered:
            if name == "User":
                continue
            buf.append(f"    public DbSet<{name}> {name}s {{ get; set; }} = null!;")

        buf.append("")
        buf.append("    protected override void OnModelCreating(ModelBuilder builder)")
        buf.append("    {")
        buf.append("        base.OnModelCreating(builder);")
        buf.append("    }")
        buf.append("}")
        return "\n".join(buf)

    # ── write ────────────────────────────────────────────────────────

    def _write_file(self, base_dir, path, filename, content):
        dir_path = os.path.join(base_dir, path.lstrip("./"))
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, filename)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"  [ok] {file_path}")

    # ── entry point ──────────────────────────────────────────────────

    def generate(self, config, project_name, output_dir="."):
        ns = self._build_namespaces(config, project_name)

        model_ns = ns.get("ModelPath", project_name)
        dto_ns = ns.get("DtoPath", project_name)
        controller_ns = ns.get("ControllerPath", project_name)
        iservice_ns = ns.get("IServicePath", ns.get("IServicesPath", project_name))
        service_ns = ns.get("ServicePath", project_name)
        mapper_ns = ns.get("MapperPath", project_name)
        enum_ns = ns.get("EnumPath", project_name)
        pagination_ns = f"{dto_ns}.Shared"

        print("\nGenerating code...")

        # ── base generic files (once) ─────────────────────────────────
        base_vars = {
            "config_dto_path": dto_ns, "config_pagination_path": pagination_ns,
            "config_iservice_path": iservice_ns, "config_service_path": service_ns,
            "config_model_path": model_ns, "config_mapper_path": mapper_ns,
            "config_controller_path": controller_ns,
        }

        isvc_base = self._substitute_template(GENERIC_ISERVICE_CSHARP, {
            k: v for k, v in base_vars.items() if k in GENERIC_ISERVICE_CSHARP
        })
        svc_base = self._substitute_template(GENERIC_SERVICE_CSHARP, {
            k: v for k, v in base_vars.items() if k in GENERIC_SERVICE_CSHARP
        })
        ctrl_base = self._substitute_template(GENERIC_CONTROLLER_CSHARP, {
            k: v for k, v in base_vars.items() if k in GENERIC_CONTROLLER_CSHARP
        })
        pag_base = self._substitute_template(GENERIC_PAGINATION_CSHARP, {"config_pagination_path": pagination_ns})
        query_base = self._substitute_template(GENERIC_QUERY_CSHARP, {"config_pagination_path": pagination_ns})

        self._write_file(output_dir, config.get("IServicesPath", config.get("IServicePath", ".")), "IGenericService.cs", isvc_base)
        self._write_file(output_dir, config["ServicePath"], "GenericService.cs", svc_base)
        self._write_file(output_dir, config["ControllerPath"], "GenericController.cs", ctrl_base)
        self._write_file(output_dir, config["DtoPath"] + "/Shared", "PaginatedResult.cs", pag_base)
        self._write_file(output_dir, config["DtoPath"] + "/Shared", "PaginateQuery.cs", query_base)

        # ── AppDbContext ──────────────────────────────────────────────
        dbcontext_ns = ns.get("DbContextPath", project_name)
        dbcontext_code = self._generate_appdbcontext(dbcontext_ns, model_ns)
        self._write_file(output_dir, config["DbContextPath"], "AppDbContext.cs", dbcontext_code)

        # ── per-table files ──────────────────────────────────────────
        for name in self._ordered:
            node = self.tables[name]
            pk_type = self._get_pk_type(node)
            table_dto_ns = f"{dto_ns}.{name}Dto"
            table_dto_path = config["DtoPath"] + f"/{name}Dto"

            model_code = self._generate_model(node, model_ns, enum_ns)
            self._write_file(output_dir, config["ModelPath"], f"{name}.cs", model_code)

            req_code = self._generate_request_dto(node, table_dto_ns, enum_ns)
            self._write_file(output_dir, table_dto_path, f"{name}RequestDto.cs", req_code)

            res_code = self._generate_response_dto(node, table_dto_ns, enum_ns)
            self._write_file(output_dir, table_dto_path, f"{name}ResponseDto.cs", res_code)

            simp_code = self._generate_response_simplified_dto(node, table_dto_ns, enum_ns)
            self._write_file(output_dir, table_dto_path, f"{name}ResponseSimplifiedDto.cs", simp_code)

            isvc_code = self._generate_iservice(name, iservice_ns, pk_type, iservice_ns, model_ns, table_dto_ns, pagination_ns)
            self._write_file(output_dir, config.get("IServicesPath", config.get("IServicePath", ".")), f"I{name}Service.cs", isvc_code)

            svc_code = self._generate_service(name, service_ns, pk_type, service_ns, iservice_ns, model_ns, table_dto_ns, pagination_ns)
            self._write_file(output_dir, config["ServicePath"], f"{name}Service.cs", svc_code)

            ctrl_code = self._generate_controller(name, controller_ns, pk_type, controller_ns, iservice_ns, table_dto_ns, pagination_ns, model_ns)
            self._write_file(output_dir, config["ControllerPath"], f"{name}Controller.cs", ctrl_code)

            map_code = self._generate_mapper(name, mapper_ns, model_ns, table_dto_ns)
            self._write_file(output_dir, config["MapperPath"], f"{name}MappingProfile.cs", map_code)

        # ── per-enum files ───────────────────────────────────────────
        for enum_node in self.enums.values():
            enum_code = self._generate_csharp_enum(enum_node, enum_ns)
            ename = enum_node.a.value
            self._write_file(output_dir, config["EnumPath"], f"{ename}.cs", enum_code)

        print("  [ok] code generation complete")



