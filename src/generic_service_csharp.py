


GENERIC_ISERVICE_CSHARP = """\
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using $$config_dto_path$$;
using $$config_pagination_path$$;

namespace $$config_iservice_path$$;

public interface IGenericService<TEntity, TDto, TRequestDto, TKey>
    where TEntity : class
    where TDto : class
    where TRequestDto : class
{
    public Task<TDto> GetByIdAsync(TKey id);
    public Task<PaginatedResult<TDto>> PaginateAsync(PaginateQuery query);
    public Task<TDto> CreateAsync(TRequestDto item);
    public Task<TDto> UpdateAsync(TKey id, TRequestDto item);
    public Task DeleteAsync(TKey id);
}
"""


GENERIC_SERVICE_CSHARP = """\
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AutoMapper;
using AutoMapper.QueryableExtensions;
using Microsoft.EntityFrameworkCore;
using $$config_iservice_path$$;
using $$config_model_path$$;
using $$config_dto_path$$;
using $$config_mapper_path$$;
using $$config_pagination_path$$;

namespace $$config_service_path$$;

public class GenericService<TEntity, TDto, TRequestDto, TKey> : IGenericService<TEntity, TDto, TRequestDto, TKey>
    where TEntity : class
    where TDto : class
    where TRequestDto : class
{
    protected readonly DbContext _context;
    protected readonly DbSet<TEntity> _table;
    protected readonly IMapper _mapper;

    public GenericService(DbContext context, IMapper mapper)
    {
        _context = context;
        _table = context.Set<TEntity>();
        _mapper = mapper;
    }

    public virtual async Task<TDto> GetByIdAsync(TKey id)
    {
        var entity = await _table.FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task<PaginatedResult<TDto>> PaginateAsync(PaginateQuery query)
    {
        var q = _table.AsQueryable();
        var totalCount = await q.CountAsync();
        var items = await q
            .Skip((query.Page - 1) * query.Rows)
            .Take(query.Rows)
            .ProjectTo<TDto>(_mapper.ConfigurationProvider)
            .ToListAsync();
        return new PaginatedResult<TDto>
        {
            Items = items,
            TotalCount = totalCount,
            Page = query.Page,
            Rows = query.Rows
        };
    }

    public virtual async Task<TDto> CreateAsync(TRequestDto item)
    {
        var entity = _mapper.Map<TEntity>(item);
        _table.Add(entity);
        await _context.SaveChangesAsync();
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task<TDto> UpdateAsync(TKey id, TRequestDto item)
    {
        var entity = await _table.FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        _mapper.Map(item, entity);
        await _context.SaveChangesAsync();
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task DeleteAsync(TKey id)
    {
        var entity = await _table.FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        _table.Remove(entity);
        await _context.SaveChangesAsync();
    }
}
"""