



GENERIC_PAGINATION_CSHARP = """\
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;

namespace {{config_dtos_path}}.shared;

public class PaginatedResult<T>
{
    public List<T> Items { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int Rows { get; set; }
    public int TotalPages => (int)Math.Ceiling((double)TotalCount / Rows);
    public bool HasPreviousPage => Page > 1;
    public bool HasNextPage => Page < TotalPages;
}
"""