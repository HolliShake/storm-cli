



GENERIC_PAGINATION_CSHARP = """\
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;

namespace $$config_pagination_path$$;

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

public static class PaginationExtensions
{
    public static async Task<PaginatedResult<T>> PaginateAsync<T>(
        this IQueryable<T> query, int page = 1, int rows = 20)
    {
        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((page - 1) * rows)
            .Take(rows)
            .ToListAsync();
        return new PaginatedResult<T>
        {
            Items = items,
            TotalCount = totalCount,
            Page = page,
            Rows = rows
        };
    }
}
"""