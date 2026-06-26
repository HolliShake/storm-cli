




from collections import deque
import os

from src.ast import AstType
from src.enum import Enum
from src.error_handler import raise_error
from src.generic_controller_csharp import GENERIC_CONTROLLER_CSHARP, GENERIC_CONTROLLER_TEMPLATE_CSHARP
from src.generic_mapper_csharp import GENERIC_MAPPER_TEMPLATE_CSHARP
from src.generic_pagination_csharp import GENERIC_PAGINATION_CSHARP
from src.generic_query_chsarp import GENERIC_QUERY_CSHARP

# ─── ANSI colors ───────────────────────────────────────────────────────────
_RST = "\033[0m"
_BLD = "\033[1m"
_GRN = "\033[32m"
_MAG = "\033[35m"

def _ok(msg):
    print(f"  {_GRN}{_BLD}[ok]{_RST} {msg}")

def _hdr(msg):
    print(f"\n{_MAG}{_BLD}{msg}{_RST}")
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

    def _get_enum_columns(self, table_node):
        """Return list of (field_name, enum_name) for enum-type columns."""
        enums = []
        enum_names = set(self.enums.keys())
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in enum_names:
                field_name = self._pascal_case(f.a.value)
                enums.append((field_name, type_name))
            f = f.next
        return enums

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

    @staticmethod
    def _camel_case(name):
        """lowercase first char — 'Owner' → 'owner', 'ownerId' → 'ownerId'."""
        if not name:
            return name
        return name[0].lower() + name[1:]

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

    def _generate_iservice(self, table_name, namespace, pk_type, iservice_ns, model_ns, dto_ns, pagination_ns, enum_ns=""):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        enum_cols = self._get_enum_columns(table_node)
        extra_methods = ""
        for fk_name, fk_table, fk_pk_type in fks:
            lower_fk = fk_name[0].lower() + fk_name[1:]
            extra_methods += f"\n    public Task<PaginatedResult<{table_name}ResponseDto>> PaginateBy{fk_name}Async({fk_pk_type} {lower_fk}Id, PaginateQuery query);"
        for enum_field, enum_name in enum_cols:
            extra_methods += f"\n    public Task<PaginatedResult<{table_name}ResponseDto>> PaginateBy{enum_field}Async({enum_name} {enum_field}, PaginateQuery query);"

        using_pagination = f"using {pagination_ns};\n" if (fks or enum_cols) else ""
        using_enum = f"using {enum_ns};\n" if enum_cols else ""

        return f"""\
{using_enum}{using_pagination}using {iservice_ns};
using {model_ns};
using {dto_ns};

namespace {namespace};

public interface I{table_name}Service : IGenericService<{table_name}, {table_name}ResponseDto, {table_name}RequestDto, {pk_type}>
{{{extra_methods}
}}
"""

    def _generate_service(self, table_name, namespace, pk_type, service_ns, iservice_ns, model_ns, dto_ns, pagination_ns, enum_ns=""):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        enum_cols = self._get_enum_columns(table_node)
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
        for enum_field, enum_name in enum_cols:
            extra_methods += f"""
    public async Task<PaginatedResult<{table_name}ResponseDto>> PaginateBy{enum_field}Async({enum_name} {enum_field}, PaginateQuery query)
    {{
        var q = _table.Where(e => e.{enum_field} == {enum_field});
        return await q
            .ProjectTo<{table_name}ResponseDto>(_mapper.ConfigurationProvider)
            .PaginateAsync(query.Page, query.Rows);
    }}
"""

        using_pagination = f"using {pagination_ns};\n" if (fks or enum_cols) else ""
        using_enum = f"using {enum_ns};\n" if enum_cols else ""

        return f"""\
{using_enum}{using_pagination}using {service_ns};
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

    def _generate_controller(self, table_name, namespace, pk_type, controller_ns, iservice_ns, dto_ns, pagination_ns, model_ns, enum_ns=""):
        table_node = self.tables[table_name]
        fks = self._get_fk_columns(table_node)
        enum_cols = self._get_enum_columns(table_node)
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
        for enum_field, enum_name in enum_cols:
            lower_enum = enum_field[0].lower() + enum_field[1:]
            extra_endpoints += f"""
    [HttpGet("{enum_name.lower()}/{{{lower_enum}}}", Name = "Get{table_name}By{enum_field}")]
    [Tags("{table_name}")]
    [EndpointSummary("Paginated list by {enum_field}")]
    [EndpointDescription("Returns a paginated list of {table_name} records filtered by {enum_field} value")]
    [ProducesResponseType(typeof(PaginatedResult<{table_name}ResponseDto>), StatusCodes.Status200OK)]
    public virtual async Task<ActionResult<PaginatedResult<{table_name}ResponseDto>>> IndexBy{enum_field}([FromRoute] {enum_name} {lower_enum},
        [FromQuery] PaginateQuery query)
    {{
        var result = await ((I{table_name}Service)_service).PaginateBy{enum_field}Async({lower_enum}, query);
        return Ok(result);
    }}
"""

        using_enum = f"using {enum_ns};\n" if enum_cols else ""

        return f"""\
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
{using_enum}using {controller_ns};
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
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        _ok(file_path)

    # ── PHP / Laravel helpers ────────────────────────────────────────

    STORM_TO_PHP = {
        "int": "int", "long": "int", "float": "float", "double": "float",
        "string": "string", "bool": "bool", "uuid": "string", "datetime": "\\DateTime",
    }

    STORM_TO_OA_TYPE = {
        "int": "integer", "long": "integer", "float": "number", "double": "number",
        "string": "string", "bool": "boolean", "uuid": "string", "datetime": "string",
    }

    STORM_TO_MIGRATION = {
        "int": "integer", "long": "bigInteger", "float": "float", "double": "double",
        "string": "string", "bool": "boolean", "uuid": "uuid", "datetime": "dateTime",
    }

    @staticmethod
    def _snake_case(name):
        """Convert PascalCase or camelCase to snake_case."""
        result = []
        for i, ch in enumerate(name):
            if ch.isupper():
                if i > 0:
                    result.append("_")
                result.append(ch.lower())
            else:
                result.append(ch)
        return "".join(result)

    def _field_php_type(self, field_node):
        """Return (php_type, is_enum, enum_name, is_fk, fk_table)."""
        type_node = field_node.b
        type_name = type_node.value.rstrip("?")
        is_nullable = type_node.value.endswith("?")

        if type_name in self.STORM_TO_PHP:
            php = self.STORM_TO_PHP[type_name]
            if is_nullable and php != "string":
                return (f"?{php}", False, None, False, None)
            return (php, False, None, False, None)

        if type_name in self.tables:
            ref_pk_type = self._get_pk_type(self.tables[type_name])
            php_pk = self.STORM_TO_PHP.get(ref_pk_type, "int")
            return (php_pk, False, None, True, type_name)

        if type_name in self.enums:
            enum_name = type_name
            if is_nullable:
                return (f"?{enum_name}", True, enum_name, False, None)
            return (enum_name, True, enum_name, False, None)

        return ("mixed", False, None, False, None)

    def _field_oa_type(self, field_node):
        """Return (oa_type, oa_format, is_enum)."""
        type_node = field_node.b
        type_name = type_node.value.rstrip("?")

        if type_name in self.STORM_TO_OA_TYPE:
            oa = self.STORM_TO_OA_TYPE[type_name]
            fmt = "date-time" if type_name == "datetime" else None
            return (oa, fmt, False)

        if type_name in self.tables:
            return ("object", None, False)

        if type_name in self.enums:
            return ("string", None, True)

        return ("string", None, False)

    # ── PHP Enum generator ───────────────────────────────────────────

    def _generate_php_enum(self, enum_node):
        name = enum_node.a.value
        lines = [
            "<?php",
            "",
            "namespace App\\Static;",
            "",
            "use OpenApi\\Attributes as OA;",
            "",
            f"#[OA\\Schema(",
            f"    schema: \"{name}\",",
            f"    title: \"{name}\",",
            f"    type: \"string\",",
            f"    enum: {name}::class,",
            f")]",
            f"enum {name}: string",
            "{",
        ]

        cur = enum_node.b
        first = True
        while cur:
            key = cur.a.value
            value = cur.b.value if cur.b else ""
            if first:
                lines.append(f"    case {key} = \"{value}\";")
                first = False
            else:
                lines.append(f"    case {key} = \"{value}\";")
            cur = cur.next

        lines.append("}")
        return "\n".join(lines)

    # ── PHP Model generator ──────────────────────────────────────────

    def _generate_php_model_oa_schemas(self, table_node):
        r"""Generate #[OA\Schema] annotations for a model."""
        name = table_node.a.value
        table_pascal = self._pascal_case(name)

        required_fields = []
        property_attrs = []

        f = table_node.b
        while f:
            field_name = self._snake_case(f.a.value)
            oa_type, oa_format, is_enum = self._field_oa_type(f)
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            is_nullable = type_node.value.endswith("?")

            # Determine if required
            pk = self._get_pk_field(table_node)
            is_pk = (pk is not None and f.a.value == pk.a.value)

            if not is_nullable and not is_pk:
                required_fields.append(field_name)
            elif type_name == "datetime":
                required_fields.append(field_name)

            # Build property
            if is_enum:
                prop = f"        new OA\\Property(property: \"{field_name}\", type: \"{oa_type}\"),"
            elif oa_format:
                prop = f"        new OA\\Property(property: \"{field_name}\", type: \"{oa_type}\", format: \"{oa_format}\"),"
            elif type_name in self.tables:
                # FK property — reference the related model
                ref_name = type_name
                prop = f"        new OA\\Property(property: \"{field_name}\", ref: \"#/components/schemas/{ref_name}\"),"
                # Also add the FK id column if not already present
                fk_col = f"{field_name}_id"
                # Only add FK id if it's NOT already in the property list AND not a PK
                fk_already = False
                f2 = table_node.b
                while f2:
                    if self._snake_case(f2.a.value) == fk_col:
                        fk_already = True
                        break
                    f2 = f2.next
                if not fk_already:
                    fk_pk = self._get_pk_type(self.tables[type_name])
                    fk_oa = self.STORM_TO_OA_TYPE.get(fk_pk, "integer")
                    property_attrs.append(
                        f"        new OA\\Property(property: \"{fk_col}\", type: \"{fk_oa}\"),"
                    )
            else:
                nullable_suffix = ", nullable: true" if is_nullable else ""
                prop = f"        new OA\\Property(property: \"{field_name}\", type: \"{oa_type}\"{nullable_suffix}),"

            property_attrs.append(prop)
            f = f.next

        required_str = ",\n        ".join(f'"{r}"' for r in required_fields)
        if required_str:
            required_block = f"    required: [\n        {required_str}\n    ],"
        else:
            required_block = ""

        properties_block = "\n".join(property_attrs)

        oa_schemas = f"""
#[OA\\Schema(
    schema: "{table_pascal}",
    title: "{table_pascal}",
    type: "object",
{required_block}
    properties: [
{properties_block}
    ]
)]

#[OA\\Schema(
    schema: "Paginated{table_pascal}",
    title: "Paginated{table_pascal}",
    type: "object",
    properties: [
        new OA\\Property(property: "data", type: "array", items: new OA\\Items(ref: "#/components/schemas/{table_pascal}")),
        new OA\\Property(property: "current_page", type: "integer"),
        new OA\\Property(property: "last_page", type: "integer"),
        new OA\\Property(property: "per_page", type: "integer"),
        new OA\\Property(property: "total", type: "integer"),
        new OA\\Property(property: "from", type: "integer", nullable: true),
        new OA\\Property(property: "to", type: "integer", nullable: true),
    ]
)]

#[OA\\Schema(
    schema: "Paginated{table_pascal}Response200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true),
        new OA\\Property(property: "data", ref: "#/components/schemas/Paginated{table_pascal}")
    ]
)]

#[OA\\Schema(
    schema: "Get{table_pascal}Response200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true),
        new OA\\Property(property: "data", ref: "#/components/schemas/{table_pascal}")
    ]
)]

#[OA\\Schema(
    schema: "Get{table_pascal}sResponse200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true),
        new OA\\Property(property: "data", type: "array", items: new OA\\Items(ref: "#/components/schemas/{table_pascal}"))
    ]
)]

#[OA\\Schema(
    schema: "Create{table_pascal}Response200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true),
        new OA\\Property(property: "data", ref: "#/components/schemas/{table_pascal}")
    ]
)]

#[OA\\Schema(
    schema: "Update{table_pascal}Response200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true),
        new OA\\Property(property: "data", ref: "#/components/schemas/{table_pascal}")
    ]
)]

#[OA\\Schema(
    schema: "Delete{table_pascal}Response200",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: true)
    ]
)]"""
        return oa_schemas

    def _get_reverse_fks(self, table_name):
        """Return list of (other_table, fk_field_name) where other_table has FK to table_name."""
        reverse = []
        for other_name, other_node in self.tables.items():
            if other_name == table_name:
                continue
            f = other_node.b
            while f:
                type_node = f.b
                type_name = type_node.value.rstrip("?")
                if type_name == table_name:
                    field_name = self._snake_case(f.a.value)
                    reverse.append((other_name, field_name))
                f = f.next
        return reverse

    def _generate_php_model(self, table_node, namespace):
        name = table_node.a.value
        table_snake = self._snake_case(name)
        name_lower = name.lower()

        # Determine which relationships exist
        has_fk = False
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                has_fk = True
                break
            f = f.next

        reverse_fks = self._get_reverse_fks(name)
        has_has_many = len(reverse_fks) > 0

        lines = [
            "<?php",
            "",
            "namespace App\\Models;",
            "",
            "use Illuminate\\Database\\Eloquent\\Model;",
        ]
        if has_fk:
            lines.append("use Illuminate\\Database\\Eloquent\\Relations\\BelongsTo;")
        if has_has_many:
            lines.append("use Illuminate\\Database\\Eloquent\\Relations\\HasMany;")
        lines.append("use OpenApi\\Attributes as OA;")

        # Add enum imports
        used_enums = self._table_uses_enums(table_node)
        for enum_name in used_enums:
            lines.append(f"use App\\Static\\{enum_name};")

        lines.append("")

        # OA Schemas
        lines.append(self._generate_php_model_oa_schemas(table_node).strip())

        lines.append(f"class {name} extends Model")
        lines.append("{")

        # $table
        lines.append(f"    protected $table = '{table_snake}';")

        # $fillable
        fillable = []
        # Collect all snake_case field names for FK-id dedup
        all_snake_fields = set()
        f = table_node.b
        while f:
            all_snake_fields.add(self._snake_case(f.a.value))
            f = f.next

        f = table_node.b
        pk = self._get_pk_field(table_node)
        while f:
            field_name = self._snake_case(f.a.value)
            if pk and f.a.value == pk.a.value:
                pass  # Skip PK from fillable
            else:
                type_node = f.b
                type_name = type_node.value.rstrip("?")
                if type_name in self.tables:
                    fk_id = f"{field_name}_id"
                    if fk_id not in all_snake_fields:
                        fillable.append(fk_id)
                else:
                    fillable.append(field_name)
            f = f.next
        if fillable:
            fillable_str = "', '".join(fillable)
            lines.append(f"    protected $fillable = ['{fillable_str}'];")

        # $casts — enum fields
        casts = []
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.enums:
                field_name = self._snake_case(f.a.value)
                casts.append(f"        '{field_name}' => {type_name}::class,")
            elif type_name == "datetime":
                field_name = self._snake_case(f.a.value)
                casts.append(f"        '{field_name}' => 'datetime',")
            f = f.next

        if casts:
            lines.append("")
            lines.append("    protected function casts(): array")
            lines.append("    {")
            lines.append("        return [")
            lines.extend(casts)
            lines.append("        ];")
            lines.append("    }")

        # Relationships — BelongsTo (FKs)
        has_rels = False
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                if not has_rels:
                    lines.append("")
                    has_rels = True
                field_name = self._snake_case(f.a.value)
                parts = field_name.split("_")
                camel_method = parts[0] + "".join(p.title() for p in parts[1:])
                lines.append(f"    public function {camel_method}(): BelongsTo")
                lines.append("    {")
                lines.append(f"        return $this->belongsTo({type_name}::class, '{field_name}_id');")
                lines.append("    }")
                lines.append("")
            f = f.next

        # Relationships — HasMany (reverse FKs)
        for other_name, fk_field in reverse_fks:
            other_snake = self._snake_case(other_name)
            other_plural = other_snake + "s"
            method_name = other_plural  # e.g. "products" for Product → User
            lines.append(f"    public function {method_name}(): HasMany")
            lines.append("    {")
            lines.append(f"        return $this->hasMany({other_name}::class, '{fk_field}_id');")
            lines.append("    }")
            lines.append("")

        lines.append("}")
        return "\n".join(lines)

    # ── PHP Controller generator ─────────────────────────────────────

    def _generate_php_controller(self, table_node, namespace):
        name = table_node.a.value
        table_pascal = self._pascal_case(name)
        table_snake = self._snake_case(name)
        table_kebab = self._snake_case(name).replace("_", "-")

        pk = self._get_pk_field(table_node)
        pk_name = self._snake_case(pk.a.value) if pk else "id"
        pk_php_type = self._field_php_type(pk)[0] if pk else "int"
        pk_oa_type = self.STORM_TO_OA_TYPE.get(
            pk.b.value.rstrip("?") if pk else "int", "integer"
        )

        # Get filterable FK columns
        fk_params = []
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                fk_col = self._snake_case(f.a.value) + "_id"
                fk_name = type_name  # PascalCase for tag
                fk_oa_type = self.STORM_TO_OA_TYPE.get(
                    self._get_pk_type(self.tables[type_name]), "integer"
                )
                fk_params.append((fk_col, fk_name, fk_oa_type))
            f = f.next

        # Build FK parameter annotations
        fk_param_lines = ""
        for fk_col, fk_name, fk_oa_type in fk_params:
            fk_param_lines += f"""
    #[OA\\Parameter(
        name: "filter[{fk_col}]",
        in: "query",
        description: "Filter by {fk_name} ID",
        required: false,
        schema: new OA\\Schema(type: "{fk_oa_type}")
    )]"""

        # Build query params for index
        searchable_text_fields = []
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name == "string":
                searchable_text_fields.append(self._snake_case(f.a.value))
            f = f.next

        # Route prefix - lowercase kebab-case
        route_prefix = table_snake.replace("_", "-")

        # ── FK paginate-by endpoints (inserted between show() and store()) ─
        fk_endpoint = ""
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                fk_field_pascal = self._pascal_case(f.a.value)
                fk_param = self._camel_case(fk_field_pascal) + "Id"  # e.g. ownerId
                fk_table_pascal = self._pascal_case(type_name)
                fk_table_lower = type_name.lower()
                fk_pk_type = self._get_pk_type(self.tables[type_name])
                fk_oa_param_type = self.STORM_TO_OA_TYPE.get(fk_pk_type, "integer")
                fk_endpoint += f"""
    #[OA\\Get(
        path: "/api/{route_prefix}/{fk_table_lower}/{{{fk_param}}}",
        summary: "Get paginated list of {table_pascal} by {fk_table_pascal}",
        tags: ["{table_pascal}"],
        description: "Retrieve a paginated list of {table_pascal} filtered by {fk_table_pascal} ID",
        operationId: "get{table_pascal}By{fk_table_pascal}",
    )]
    #[OA\\Parameter(
        name: "{fk_param}",
        in: "path",
        required: true,
        schema: new OA\\Schema(type: "{fk_oa_param_type}")
    )]
    #[OA\\Parameter(
        name: "page",
        in: "query",
        description: "Page number",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 1)
    )]
    #[OA\\Parameter(
        name: "rows",
        in: "query",
        description: "Number of items per page",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 10)
    )]
    #[OA\\Response(
        response: 200,
        description: "Successful operation",
        content: new OA\\JsonContent(ref: "#/components/schemas/Paginated{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    public function indexBy{fk_table_pascal}(${fk_param}): JsonResponse
    {{
        $data = $this->service->paginateBy{fk_table_pascal}(${fk_param}, request()->only(['page', 'rows']));
        return $this->ok($data);
    }}
"""
            f = f.next

        # ── Enum-value paginate-by endpoints ──────────────────────────
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.enums:
                field_pascal = self._pascal_case(f.a.value)
                field_snake = self._snake_case(f.a.value)
                enum_name = type_name
                fk_endpoint += f"""
    #[OA\\Get(
        path: "/api/{route_prefix}/{enum_name.lower()}/{{{field_snake}}}",
        summary: "Get paginated list of {table_pascal} by {field_pascal}",
        tags: ["{table_pascal}"],
        description: "Retrieve a paginated list of {table_pascal} filtered by {field_pascal} value",
        operationId: "get{table_pascal}By{field_pascal}",
    )]
    #[OA\\Parameter(
        name: "{field_snake}",
        in: "path",
        required: true,
        schema: new OA\\Schema(type: "string")
    )]
    #[OA\\Parameter(
        name: "page",
        in: "query",
        description: "Page number",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 1)
    )]
    #[OA\\Parameter(
        name: "rows",
        in: "query",
        description: "Number of items per page",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 10)
    )]
    #[OA\\Response(
        response: 200,
        description: "Successful operation",
        content: new OA\\JsonContent(ref: "#/components/schemas/Paginated{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    public function indexBy{field_pascal}(${field_snake}): JsonResponse
    {{
        $data = $this->service->paginateBy{field_pascal}(${field_snake}, request()->only(['page', 'rows']));
        return $this->ok($data);
    }}
"""
            f = f.next

        code = f"""<?php

namespace App\\Controllers;

use App\\Services\\{table_pascal}Service;
use Illuminate\\Database\\Eloquent\\ModelNotFoundException;
use Illuminate\\Http\\JsonResponse;
use Illuminate\\Http\\Request;
use Illuminate\\Routing\\Controller;
use OpenApi\\Attributes as OA;

class {table_pascal}Controller extends Controller
{{
    public function __construct(
        protected {table_pascal}Service $service
    ) {{
    }}

    #[OA\\Get(
        path: "/api/{route_prefix}",
        summary: "Get paginated list of {table_pascal}",
        tags: ["{table_pascal}"],
        description: "Retrieve a paginated list of {table_pascal} with optional search",
        operationId: "get{table_pascal}Paginated",
    )]
    #[OA\\Parameter(
        name: "search",
        in: "query",
        description: "Search term",
        required: false,
        schema: new OA\\Schema(type: "string")
    )]
    #[OA\\Parameter(
        name: "page",
        in: "query",
        description: "Page number",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 1)
    )]
    #[OA\\Parameter(
        name: "rows",
        in: "query",
        description: "Number of items per page",
        required: false,
        schema: new OA\\Schema(type: "integer", default: 10)
    )]{fk_param_lines}
    #[OA\\Response(
        response: 200,
        description: "Successful operation",
        content: new OA\\JsonContent(ref: "#/components/schemas/Paginated{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    public function index(Request $request): JsonResponse
    {{
        $filters = $request->query('filter', []);
        $data = $this->service->paginate(
            $request->query('search'),
            array_merge($request->only(['page', 'rows']), $filters ? ['filter' => $filters] : [])
        );
        return $this->ok($data);
    }}

    #[OA\\Get(
        path: "/api/{route_prefix}/{{{pk_name}}}",
        summary: "Get a specific {table_pascal}",
        tags: ["{table_pascal}"],
        description: "Retrieve a {table_pascal} by its ID",
        operationId: "get{table_pascal}ById",
    )]
    #[OA\\Parameter(
        name: "{pk_name}",
        in: "path",
        required: true,
        schema: new OA\\Schema(type: "{pk_oa_type}")
    )]
    #[OA\\Response(
        response: 200,
        description: "Successful operation",
        content: new OA\\JsonContent(ref: "#/components/schemas/Get{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    #[OA\\Response(
        response: 404,
        description: "{table_pascal} not found"
    )]
    public function show(${pk_name}): JsonResponse
    {{
        try {{
            return $this->ok($this->service->getById(${pk_name}));
        }} catch (ModelNotFoundException $e) {{
            return $this->notFound('{table_pascal} not found');
        }}
    }}
{fk_endpoint}
    #[OA\\Post(
        path: "/api/{route_prefix}/create",
        summary: "Create a new {table_pascal}",
        tags: ["{table_pascal}"],
        description: "Create a new {table_pascal} with the provided details",
        operationId: "create{table_pascal}",
    )]
    #[OA\\RequestBody(
        required: true,
        content: new OA\\JsonContent(ref: "#/components/schemas/{table_pascal}")
    )]
    #[OA\\Response(
        response: 200,
        description: "{table_pascal} created successfully",
        content: new OA\\JsonContent(ref: "#/components/schemas/Create{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    #[OA\\Response(
        response: 422,
        description: "Validation error",
        content: new OA\\JsonContent(ref: "#/components/schemas/ValidationErrorResponse")
    )]
    #[OA\\Response(
        response: 500,
        description: "Internal server error",
        content: new OA\\JsonContent(ref: "#/components/schemas/InternalServerErrorResponse")
    )]
    public function store(Request $request): JsonResponse
    {{
        $data = $request->validate($this->service->rules());
        return $this->ok($this->service->create($data));
    }}

    #[OA\\Put(
        path: "/api/{route_prefix}/update/{{{pk_name}}}",
        summary: "Update a {table_pascal}",
        tags: ["{table_pascal}"],
        description: "Update an existing {table_pascal} with the provided details",
        operationId: "update{table_pascal}",
    )]
    #[OA\\Parameter(
        name: "{pk_name}",
        in: "path",
        required: true,
        schema: new OA\\Schema(type: "{pk_oa_type}"),
    )]
    #[OA\\RequestBody(
        required: true,
        content: new OA\\JsonContent(ref: "#/components/schemas/{table_pascal}")
    )]
    #[OA\\Response(
        response: 200,
        description: "{table_pascal} updated successfully",
        content: new OA\\JsonContent(ref: "#/components/schemas/Update{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    #[OA\\Response(
        response: 404,
        description: "{table_pascal} not found"
    )]
    #[OA\\Response(
        response: 422,
        description: "Validation error",
        content: new OA\\JsonContent(ref: "#/components/schemas/ValidationErrorResponse")
    )]
    #[OA\\Response(
        response: 500,
        description: "Internal server error",
        content: new OA\\JsonContent(ref: "#/components/schemas/InternalServerErrorResponse")
    )]
    public function update(Request $request, ${pk_name}): JsonResponse
    {{
        $data = $request->validate($this->service->rules(${pk_name}));
        try {{
            return $this->ok($this->service->update(${pk_name}, $data));
        }} catch (ModelNotFoundException $e) {{
            return $this->notFound('{table_pascal} not found');
        }}
    }}

    #[OA\\Delete(
        path: "/api/{route_prefix}/delete/{{{pk_name}}}",
        summary: "Delete a {table_pascal}",
        tags: ["{table_pascal}"],
        description: "Delete a {table_pascal} by its ID",
        operationId: "delete{table_pascal}",
    )]
    #[OA\\Parameter(
        name: "{pk_name}",
        in: "path",
        required: true,
        schema: new OA\\Schema(type: "{pk_oa_type}")
    )]
    #[OA\\Response(
        response: 200,
        description: "{table_pascal} deleted successfully",
        content: new OA\\JsonContent(ref: "#/components/schemas/Delete{table_pascal}Response200")
    )]
    #[OA\\Response(
        response: 401,
        description: "Unauthenticated",
        content: new OA\\JsonContent(ref: "#/components/schemas/UnauthenticatedResponse")
    )]
    #[OA\\Response(
        response: 403,
        description: "Forbidden",
        content: new OA\\JsonContent(ref: "#/components/schemas/ForbiddenResponse")
    )]
    #[OA\\Response(
        response: 404,
        description: "{table_pascal} not found"
    )]
    #[OA\\Response(
        response: 500,
        description: "Internal server error",
        content: new OA\\JsonContent(ref: "#/components/schemas/InternalServerErrorResponse")
    )]
    public function destroy(${pk_name}): JsonResponse
    {{
        try {{
            $this->service->delete(${pk_name});
            return $this->ok(null, '{table_pascal} deleted successfully');
        }} catch (ModelNotFoundException $e) {{
            return $this->notFound('{table_pascal} not found');
        }}
    }}
}}"""
        return code

    # ── PHP Service generator ─────────────────────────────────────────

    def _generate_php_service(self, table_node, namespace):
        name = table_node.a.value
        table_pascal = self._pascal_case(name)
        table_snake = self._snake_case(name)

        # Build validation rules
        rules_lines = []
        f = table_node.b
        pk = self._get_pk_field(table_node)
        while f:
            field_name = self._snake_case(f.a.value)
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            is_nullable = type_node.value.endswith("?")
            if pk and f.a.value == pk.a.value:
                f = f.next
                continue

            ts = self.STORM_TO_MIGRATION.get(type_name, "string")
            rules = []
            if not is_nullable:
                rules.append("required")
            else:
                rules.append("nullable")

            if ts in ("integer", "bigInteger"):
                rules.append("integer")
            elif ts in ("float", "double"):
                rules.append("numeric")
            elif ts == "string":
                rules.append("string")
                # Extract max from attrs if present
                if type_node.a and type_node.a.a:
                    cur = type_node.a.a
                    while cur:
                        if cur.a.value == "max":
                            try:
                                rules.append(f"max:{cur.b.value}")
                            except (ValueError, AttributeError):
                                pass
                        cur = cur.next
            elif ts == "uuid":
                rules.append("uuid")
            elif ts == "boolean":
                rules.append("boolean")
            elif ts == "dateTime":
                rules.append("date")

            if type_name in self.tables:
                rules.append(f"exists:{self._snake_case(type_name)},id")

            rules_lines.append(f"            '{field_name}' => '{'|'.join(rules)}',")
            f = f.next

        rules_block = "\n".join(rules_lines)

        # FK fields for filters
        fk_filters = []
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                fk_col = self._snake_case(f.a.value) + "_id"
                fk_filters.append(fk_col)
            f = f.next

        has_filters_line = f"    protected array $filterable = ['" + "', '".join(fk_filters) + "'];" if fk_filters else "    protected array $filterable = [];"

        # FK pagination methods (like C# PaginateByOwnerAsync)
        fk_methods = ""
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.tables:
                fk_field_pascal = self._pascal_case(f.a.value)
                fk_param = self._camel_case(fk_field_pascal) + "Id"  # e.g. ownerId
                fk_db_col = self._snake_case(f.a.value) + "_id"     # e.g. owner_id (DB column)
                fk_table_pascal = self._pascal_case(type_name)
                fk_methods += f"""
    public function paginateBy{fk_table_pascal}(mixed ${fk_param}, array $options = []): \\Illuminate\\Contracts\\Pagination\\LengthAwarePaginator
    {{
        $query = {table_pascal}::where('{fk_db_col}', ${fk_param});

        $page = (int)($options['page'] ?? 1);
        $rows = (int)($options['rows'] ?? 10);

        return $query->paginate($rows, ['*'], 'page', $page);
    }}
"""
            f = f.next

        # Enum pagination methods (like C# PaginateByStatusAsync)
        f = table_node.b
        while f:
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            if type_name in self.enums:
                field_pascal = self._pascal_case(f.a.value)
                field_snake = self._snake_case(f.a.value)
                enum_name = type_name
                fk_methods += f"""
    public function paginateBy{field_pascal}(${field_snake}, array $options = []): \\Illuminate\\Contracts\\Pagination\\LengthAwarePaginator
    {{
        $query = {table_pascal}::where('{field_snake}', ${field_snake});

        $page = (int)($options['page'] ?? 1);
        $rows = (int)($options['rows'] ?? 10);

        return $query->paginate($rows, ['*'], 'page', $page);
    }}
"""
            f = f.next

        return f"""<?php

namespace App\\Services;

use App\\Models\\{table_pascal};
use Illuminate\\Database\\Eloquent\\ModelNotFoundException;

class {table_pascal}Service
{{
{has_filters_line}

    /** Searchable text fields. */
    protected array $searchable = ['name'];

    public function paginate(?string $search = null, array $options = [])
    {{
        $query = {table_pascal}::query();

        if ($search && $this->searchable) {{
            $query->where(function ($q) use ($search) {{
                foreach ($this->searchable as $field) {{
                    $q->orWhere($field, 'like', "%{{$search}}%");
                }}
            }});
        }}

        // Apply filters
        $filters = $options['filter'] ?? [];
        foreach ($filters as $key => $value) {{
            if (in_array($key, $this->filterable)) {{
                $query->where($key, $value);
            }}
        }}

        $page = (int)($options['page'] ?? 1);
        $rows = (int)($options['rows'] ?? 10);

        return $query->paginate($rows, ['*'], 'page', $page);
    }}

    public function getById($id): {table_pascal}
    {{
        return {table_pascal}::findOrFail($id);
    }}
{fk_methods}
    public function create(array $data): {table_pascal}
    {{
        return {table_pascal}::create($data);
    }}

    public function update($id, array $data): {table_pascal}
    {{
        $model = {table_pascal}::findOrFail($id);
        $model->update($data);
        return $model->fresh();
    }}

    public function delete($id): void
    {{
        $model = {table_pascal}::findOrFail($id);
        $model->delete();
    }}

    public function rules($id = null): array
    {{
        return [
{rules_block}
        ];
    }}
}}"""

    # ── PHP Migration generator ───────────────────────────────────────

    def _generate_php_migration(self, table_node, namespace):
        name = table_node.a.value
        table_snake = self._snake_case(name)
        table_plural = table_snake + "s"  # Simple plural

        lines = [
            "<?php",
            "",
            "use Illuminate\\Database\\Migrations\\Migration;",
            "use Illuminate\\Database\\Schema\\Blueprint;",
            "use Illuminate\\Support\\Facades\\Schema;",
            "",
            "return new class extends Migration",
            "{",
            "    public function up(): void",
            "    {",
            f"        Schema::create('{table_plural}', function (Blueprint $table) {{",
        ]

        f = table_node.b
        pk = self._get_pk_field(table_node)
        has_pk = False
        while f:
            field_name = self._snake_case(f.a.value)
            type_node = f.b
            type_name = type_node.value.rstrip("?")
            is_nullable = type_node.value.endswith("?")

            ts = self.STORM_TO_MIGRATION.get(type_name)

            if pk and f.a.value == pk.a.value:
                # Primary key
                if ts == "uuid":
                    lines.append(f"            $table->uuid('{field_name}')->primary();")
                elif ts == "integer":
                    lines.append(f"            $table->id('{field_name}');")
                else:
                    lines.append(f"            $table->id('{field_name}');")
                has_pk = True
            elif type_name in self.tables:
                # Foreign key with cascade delete
                lines.append(f"            $table->foreignId('{field_name}_id')->constrained('{self._snake_case(type_name)}s')->onDelete('cascade');")
            elif ts:
                col_def = f"            $table->{ts}('{field_name}')"
                if is_nullable:
                    col_def += "->nullable()"
                if ts == "string":
                    max_len = 255
                    # Check for max attribute
                    if type_node.a:
                        attrs_node = type_node.a
                        if attrs_node and attrs_node.a:
                            cur = attrs_node.a
                            while cur:
                                if cur.a.value == "max":
                                    try:
                                        max_len = int(cur.b.value)
                                    except ValueError:
                                        pass
                                cur = cur.next
                    col_def = f"            $table->string('{field_name}', {max_len})"
                    if is_nullable:
                        col_def += "->nullable()"
                lines.append(col_def + ";")
            f = f.next

        # Add timestamps if not already present
        has_created = False
        has_updated = False
        f = table_node.b
        while f:
            fn = self._snake_case(f.a.value)
            if fn == "created_at":
                has_created = True
            if fn == "updated_at":
                has_updated = True
            f = f.next
        if has_created and has_updated:
            pass  # Handled by field decls above
        else:
            lines.append("            $table->timestamps();")

        lines.append("        });")
        lines.append("    }")
        lines.append("")
        lines.append("    public function down(): void")
        lines.append("    {")
        lines.append(f"        Schema::dropIfExists('{table_plural}');")
        lines.append("    }")
        lines.append("};")

        return "\n".join(lines)

    # ── PHP Base Controller ───────────────────────────────────────────

    PHP_BASE_CONTROLLER = """<?php

namespace App\\Controllers;

use Illuminate\\Routing\\Controller as BaseController;
use Illuminate\\Http\\JsonResponse;
use OpenApi\\Attributes as OA;

#[OA\\Schema(
    schema: "UnauthenticatedResponse",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: false),
        new OA\\Property(property: "message", type: "string", example: "Unauthenticated"),
    ]
)]
#[OA\\Schema(
    schema: "ForbiddenResponse",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: false),
        new OA\\Property(property: "message", type: "string", example: "Forbidden"),
    ]
)]
#[OA\\Schema(
    schema: "ValidationErrorResponse",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: false),
        new OA\\Property(property: "message", type: "string", example: "Validation error"),
        new OA\\Property(property: "errors", type: "object"),
    ]
)]
#[OA\\Schema(
    schema: "InternalServerErrorResponse",
    type: "object",
    properties: [
        new OA\\Property(property: "success", type: "boolean", example: false),
        new OA\\Property(property: "message", type: "string", example: "Internal server error"),
    ]
)]
class Controller extends BaseController
{
    protected function ok(mixed $data = null, string $message = 'Success', int $status = 200): JsonResponse
    {
        $response = [
            'success' => true,
            'message' => $message,
        ];
        if ($data !== null) {
            $response['data'] = $data;
        }
        return response()->json($response, $status);
    }

    protected function notFound(string $message = 'Resource not found'): JsonResponse
    {
        return response()->json([
            'success' => false,
            'message' => $message,
        ], 404);
    }
}"""

    # ── PHP Route generator ───────────────────────────────────────────

    def _generate_php_routes(self):
        """Generate routes/api.php with all resource routes."""
        lines = [
            "<?php",
            "",
            "use Illuminate\\Support\\Facades\\Route;",
            "use App\\Controllers\\Controller;",
        ]

        for name in self._ordered:
            name_pascal = self._pascal_case(name)
            name_kebab = self._snake_case(name).replace("_", "-")
            lines.append(f"use App\\Controllers\\{name_pascal}Controller;")

        lines.append("")
        lines.append("Route::prefix('api')->group(function () {")

        for name in self._ordered:
            name_pascal = self._pascal_case(name)
            name_kebab = self._snake_case(name).replace("_", "-")
            lines.append(f"    Route::get('/{name_kebab}', [{name_pascal}Controller::class, 'index']);")
            lines.append(f"    Route::get('/{name_kebab}/{{id}}', [{name_pascal}Controller::class, 'show']);")

            # FK paginate-by routes
            node = self.tables[name]
            f = node.b
            while f:
                type_node = f.b
                type_name = type_node.value.rstrip("?")
                if type_name in self.tables:
                    fk_param = self._camel_case(self._pascal_case(f.a.value)) + "Id"  # ownerId
                    fk_table_lower = type_name.lower()  # user
                    fk_table_pascal = self._pascal_case(type_name)
                    lines.append(f"    Route::get('/{name_kebab}/{fk_table_lower}/{{{fk_param}}}', [{name_pascal}Controller::class, 'indexBy{fk_table_pascal}']);")
                f = f.next

            # Enum-value paginate-by routes
            f = node.b
            while f:
                type_node = f.b
                type_name = type_node.value.rstrip("?")
                if type_name in self.enums:
                    field_snake = self._snake_case(f.a.value)
                    field_pascal = self._pascal_case(f.a.value)
                    enum_lower = type_name.lower()
                    lines.append(f"    Route::get('/{name_kebab}/{enum_lower}/{{{field_snake}}}', [{name_pascal}Controller::class, 'indexBy{field_pascal}']);")
                f = f.next

            lines.append(f"    Route::post('/{name_kebab}/create', [{name_pascal}Controller::class, 'store']);")
            lines.append(f"    Route::put('/{name_kebab}/update/{{id}}', [{name_pascal}Controller::class, 'update']);")
            lines.append(f"    Route::delete('/{name_kebab}/delete/{{id}}', [{name_pascal}Controller::class, 'destroy']);")
            lines.append("")

        lines.append("});")
        return "\n".join(lines)

    # ── PHP AppServiceProvider ────────────────────────────────────────

    PHP_APP_SERVICE_PROVIDER = """<?php

namespace App\\Providers;

use Illuminate\\Support\\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        // Bind services here
    }

    public function boot(): void
    {
        //
    }
}"""

    # ── entry point ──────────────────────────────────────────────────

    def generate(self, config, project_name, output_dir="."):
        # Detect template: Laravel = MigrationsPath present, C# = DbContextPath
        is_laravel = "MigrationsPath" in config

        if is_laravel:
            self._generate_laravel(config, output_dir)
        else:
            self._generate_csharp(config, project_name, output_dir)

    def _generate_laravel(self, config, output_dir):
        """Generate PHP/Laravel code from the schema."""
        _hdr("Generating Laravel PHP code...")

        # ── Base Controller ───────────────────────────────────────────
        self._write_file(
            output_dir, config["ControllerPath"], "Controller.php",
            self.PHP_BASE_CONTROLLER,
        )

        # ── Enums ─────────────────────────────────────────────────────
        for enum_node in self.enums.values():
            enum_code = self._generate_php_enum(enum_node)
            ename = enum_node.a.value
            self._write_file(output_dir, config["EnumPath"], f"{ename}.php", enum_code)

        # ── Per-table files ───────────────────────────────────────────
        for name in self._ordered:
            node = self.tables[name]

            # Model
            model_code = self._generate_php_model(node, config["ModelPath"])
            self._write_file(output_dir, config["ModelPath"], f"{name}.php", model_code)

            # Service
            svc_code = self._generate_php_service(node, config["ServicePath"])
            self._write_file(output_dir, config["ServicePath"], f"{name}Service.php", svc_code)

            # Controller
            ctrl_code = self._generate_php_controller(node, config["ControllerPath"])
            self._write_file(output_dir, config["ControllerPath"], f"{name}Controller.php", ctrl_code)

            # Migration
            mig_code = self._generate_php_migration(node, config["MigrationsPath"])
            # Migration filename uses timestamp prefix
            import datetime
            ts = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
            table_snake = self._snake_case(name)
            mig_filename = f"{ts}_create_{table_snake}s_table.php"
            self._write_file(output_dir, config["MigrationsPath"], mig_filename, mig_code)

        # ── Routes ────────────────────────────────────────────────────
        routes_code = self._generate_php_routes()
        self._write_file(output_dir, "routes", "api.php", routes_code)

        _ok("code generation complete")
        return

    # ── C# / .NET generation ─────────────────────────────────────
    def _generate_csharp(self, config, project_name, output_dir):
        ns = self._build_namespaces(config, project_name)

        is_clean = "IServicesPath" in config
        if is_clean:
            # Clean architecture: each layer project (DOMAIN, APPLICATION,
            # INFRASTRUCTURE, API) is its own assembly with its own root
            # namespace matching the layer name — do NOT prefix with project_name.
            prefix = f"{project_name}."
            ns = {k: v[len(prefix):] if v.startswith(prefix) else v for k, v in ns.items()}

        model_ns = ns.get("ModelPath", project_name)
        dto_ns = ns.get("DtoPath", project_name)
        controller_ns = ns.get("ControllerPath", project_name)
        iservice_ns = ns.get("IServicePath", ns.get("IServicesPath", project_name))
        service_ns = ns.get("ServicePath", project_name)
        mapper_ns = ns.get("MapperPath", project_name)
        enum_ns = ns.get("EnumPath", project_name)
        pagination_ns = f"{dto_ns}.Shared"

        _hdr("Generating code...")

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

        # ── Program.cs ───────────────────────────────────────────────
        is_clean = "IServicesPath" in config
        proj_ns = project_name
        first_svc = f"{self._ordered[0]}Service" if self._ordered else "Service"
        svc_ns = service_ns
        dbcontext_ns = ns.get("DbContextPath", project_name)

        usings = [
            "using System.Reflection;",
            "using Microsoft.AspNetCore.Identity;",
            "using Microsoft.EntityFrameworkCore;",
            "using Scrutor;",
            "using Scalar.AspNetCore;",
        ]
        if is_clean:
            usings += [
                f"using {model_ns};",
                f"using {iservice_ns};",
                f"using {dto_ns}.Shared;",
                f"using {dbcontext_ns};",
                f"using {service_ns};",
                f"using {mapper_ns};",
            ]
        else:
            usings += [
                f"using {proj_ns}.Data;",
                f"using {proj_ns}.IServices;",
                f"using {proj_ns}.Services;",
                f"using {proj_ns}.Mappers;",
                f"using {proj_ns}.Models;",
            ]

        pg_content = f"""\
{chr(10).join(usings)}

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

// ── Identity ────────────────────────────────────────────────────────
builder.Services.AddIdentity<User, IdentityRole<Guid>>()
    .AddEntityFrameworkStores<AppDbContext>()
    .AddTokenProvider<DataProtectorTokenProvider<User>>(TokenOptions.DefaultProvider)
    .AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(options =>
{{
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
}});

builder.Services.Configure<IdentityOptions>(options =>
{{
    options.Password.RequireDigit = false;
    options.Password.RequireLowercase = false;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequireUppercase = false;
    options.Password.RequiredLength = 3;
    options.Password.RequiredUniqueChars = 0;
    options.User.RequireUniqueEmail = true;
}});

// Register AutoMapper with the executing assembly
builder.Services.AddAutoMapper(cfg =>
{{
    cfg.AddMaps(Assembly.GetExecutingAssembly());
}});

// Register all services that inherit from GenericService<,,,> in the assembly of {first_svc}
builder.Services.Scan(scan => scan
    .FromAssemblyOf<{first_svc}>()
    .AddClasses(classes => classes
        .InNamespaces("{svc_ns}")
        .AssignableTo(typeof(GenericService<,,,>)))
    .AsImplementedInterfaces()
    .WithScopedLifetime());

builder.Services.AddControllers();
builder.Services.AddOpenApi();

var app = builder.Build();

// ── Swagger / Scalar ────────────────────────────────────────────────
app.UseSwagger(options =>
{{
    options.RouteTemplate = "openapi/{{documentName}}.json";
}});
app.MapScalarApiReference(options =>
{{
    options.WithTitle("{proj_ns}");
    options.WithTheme(ScalarTheme.BluePlanet);
    options.WithDefaultHttpClient(ScalarTarget.JavaScript, ScalarClient.Axios);
    options.AddPreferredSecuritySchemes("Bearer");
}});

app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();
"""
        if is_clean:
            self._write_file(output_dir, "API", "Program.cs", pg_content)
        else:
            self._write_file(output_dir, ".", "Program.cs", pg_content)

        # ── AppDbContext ──────────────────────────────────────────────
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

            isvc_code = self._generate_iservice(name, iservice_ns, pk_type, iservice_ns, model_ns, table_dto_ns, pagination_ns, enum_ns)
            self._write_file(output_dir, config.get("IServicesPath", config.get("IServicePath", ".")), f"I{name}Service.cs", isvc_code)

            svc_code = self._generate_service(name, service_ns, pk_type, service_ns, iservice_ns, model_ns, table_dto_ns, pagination_ns, enum_ns)
            self._write_file(output_dir, config["ServicePath"], f"{name}Service.cs", svc_code)

            ctrl_code = self._generate_controller(name, controller_ns, pk_type, controller_ns, iservice_ns, table_dto_ns, pagination_ns, model_ns, enum_ns)
            self._write_file(output_dir, config["ControllerPath"], f"{name}Controller.cs", ctrl_code)

            map_code = self._generate_mapper(name, mapper_ns, model_ns, table_dto_ns)
            self._write_file(output_dir, config["MapperPath"], f"{name}MappingProfile.cs", map_code)

        # ── per-enum files ───────────────────────────────────────────
        for enum_node in self.enums.values():
            enum_code = self._generate_csharp_enum(enum_node, enum_ns)
            ename = enum_node.a.value
            self._write_file(output_dir, config["EnumPath"], f"{ename}.cs", enum_code)

        _ok("code generation complete")



