




GENERIC_QUERY_CSHARP = """\

namespace $$config_pagination_path$$;

public class PaginateQuery
{
    public string? Search { get; set; }

    public int Page { get; set; } = 1;

    public int Rows { get; set; } = 20;
}
"""