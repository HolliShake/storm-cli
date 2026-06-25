


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
public class GenericController<TEntity, TDto, TRequestDto, TKey> : ControllerBase
    where TEntity : class
    where TDto : class
    where TRequestDto : class
{
    protected readonly IGenericService<TEntity, TDto, TRequestDto, TKey> _service;

    public GenericController(IGenericService<TEntity, TDto, TRequestDto, TKey> service)
    {
        _service = service;
    }
}
"""

GENERIC_CONTROLLER_TEMPLATE_CSHARP = """\
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using $$config_iservice_path$$;
using $$config_dto_path$$;
using $$config_mapper_path$$;
using $$config_pagination_path$$;

namespace $$config_controller_path$$;

[ApiController]
[Route("api/[controller]")]
public class GenericController<TEntity, TDto, TKey> : GenericController<$Entity$, $TDto$, $TRequestDto$, $TKey$>
    where TEntity : class
    where TDto : class
{
    [HttpGet("{id}")]
    [Tags("$Entity$")]
    [EndpointSummary("Retrieve by id")]
    [EndpointDescription("Returns a single record by its unique identifier")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<$TDto$>> Show($TKey$ id)
    {
        var result = await _service.GetByIdAsync(id);
        return Ok(result);
    }

    [HttpGet]
    [Tags("$Entity$")]
    [EndpointSummary("Paginated list")]
    [EndpointDescription("Returns a paginated list of records")]
    [ProducesResponseType(typeof(PaginatedResult<$TDto$>), StatusCodes.Status200OK)]
    public virtual async Task<ActionResult<PaginatedResult<$TDto$>>> Index(
        [FromQuery] int page = 1,
        [FromQuery] int rows = 20)
    {
        var result = await _service.PaginateAsync(page, rows);
        return Ok(result);
    }

    [HttpPost]
    [Tags("$Entity$")]
    [EndpointSummary("Create new")]
    [EndpointDescription("Creates a new record from the provided payload")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public virtual async Task<ActionResult<$TDto$>> Store([FromBody] $TRequestDto$ item)
    {
        var result = await _service.CreateAsync(item);
        return Ok(result);
    }

    [HttpPut("{id}")]
    [Tags("$Entity$")]
    [EndpointSummary("Update by id")]
    [EndpointDescription("Updates an existing record identified by its id with the provided payload")]
    [ProducesResponseType(typeof($TDto$), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<ActionResult<$TDto$>> Update($TKey$ id, [FromBody] $TRequestDto$ item)
    {
        var result = await _service.UpdateAsync(id, item);
        return Ok(result);
    }

    [HttpDelete("{id}")]
    [Tags("$Entity$")]
    [EndpointSummary("Delete by id")]
    [EndpointDescription("Deletes a record by its unique identifier")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public virtual async Task<IActionResult> Destroy($TKey$ id)
    {
        await _service.DeleteAsync(id);
        return NoContent();
    }
}
"""
