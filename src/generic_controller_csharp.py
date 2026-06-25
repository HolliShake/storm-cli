


GENERIC_CONTROLLER_CSHARP = """\
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using $$config_iservice_path$$;
using $$config_dto_path$$;
using $$config_mapper_path$$;
using $$config_pagination_path$$;

namespace $$config_controller_path$$;

[ApiController]
[Route("api/[controller]")]
public class GenericController<TEntity, TDto, TKey> : ControllerBase
    where TEntity : class
    where TDto : class
{
    protected readonly IGenericService<TEntity, TDto, TKey> _service;

    public GenericController(IGenericService<TEntity, TDto, TKey> service)
    {
        _service = service;
    }
}
"""

GENERIC_CONTROLLER_TEMPLATE_CSHARP = """\
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Swashbuckle.AspNetCore.Annotations;
using $$config_iservice_path$$;
using $$config_dto_path$$;
using $$config_mapper_path$$;
using $$config_pagination_path$$;

namespace $$config_controller_path$$;

[ApiController]
[Route("api/[controller]")]
public class GenericController<TEntity, TDto, TKey> : GenericController<$Entity$, $TDto$, $TKey$>
    where TEntity : class
    where TDto : class
{
    [HttpGet("{id}")]
    [SwaggerOperation(
        Tags = [ "$Entity$" ],
        Summary = "Retrieve by id",
        Description = "Returns a single record by its unique identifier",
        OperationId = "Show")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<$TDto$>> Show($TKey$ id)
    {
        var result = await _service.GetByIdAsync(id);
        return Ok(result);
    }

    [HttpGet]
    [SwaggerOperation(
        Tags = [ "$Entity$" ],
        Summary = "Paginated list",
        Description = "Returns a paginated list of records",
        OperationId = "Index")]
    [ProducesResponseType(typeof(PaginatedResult<$TDto$>), StatusCodes.Status200OK)]
    public virtual async Task<ActionResult<PaginatedResult<$TDto$>>> Index(
        [FromQuery] int page = 1,
        [FromQuery] int rows = 20)
    {
        var result = await _service.PaginateAsync(page, rows);
        return Ok(result);
    }

    [HttpPost]
    [SwaggerOperation(
        Tags = [ "$Entity$" ],
        Summary = "Create new",
        Description = "Creates a new record from the provided payload",
        OperationId = "Store")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public virtual async Task<ActionResult<$TDto$>> Store([FromBody] $TDto$ item)
    {
        var result = await _service.CreateAsync(item);
        return Ok(result);
    }

    [HttpPut("{id}")]
    [SwaggerOperation(
        Tags = [ "$Entity$" ],
        Summary = "Update by id",
        Description = "Updates an existing record identified by its id with the provided payload",
        OperationId = "Update")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<$TDto$>> Update($TKey$ id, [FromBody] $TDto$ item)
    {
        var result = await _service.UpdateAsync(id, item);
        return Ok(result);
    }

    [HttpDelete("{id}")]
    [SwaggerOperation(
        Tags = [ "$Entity$" ],
        Summary = "Delete by id",
        Description = "Deletes a record by its unique identifier",
        OperationId = "Destroy")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<IActionResult> Destroy($TKey$ id)
    {
        await _service.DeleteAsync(id);
        return NoContent();
    }
}
"""
