




GENERIC_QUERY_CSHARP = """\
using Microsoft.AspNetCore.Mvc;

namespace $$config_pagination_path$$;

public class PaginateQuery
{
    [FromQuery]
    public string? Search { get; set; }

    [FromQuery]
    public int Page { get; set; } = 1;

    [FromQuery]
    public int Rows { get; set; } = 20;
}
"""