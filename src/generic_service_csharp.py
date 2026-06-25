


GENERIC_ISERVICE_CSHARP = """\
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using $config_dto_path$;
using $config_pagination_path$;

namespace $config_iservice_path$;

public interface IGenericService<TEntity, TDto, TKey>
    where TEntity : class
    where TDto : class
{
    public Task<TDto> GetByIdAsync(TKey id);
    public Task<PaginatedResult<TDto>> PaginateAsync(int page = 1, int rows = 20);
    public Task<TDto> CreateAsync(TDto item);
    public Task<TDto> UpdateAsync(TKey id, TDto item);
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
using $config_iservice_path$;
using $config_model_path$;
using $config_dto_path$;
using $config_mapper_path$;
using $config_pagination_path$;

namespace $config_service_path$;

public class GenericService<TEntity, TDto, TKey> : IGenericService<TEntity, TDto, TKey>
    where TEntity : class
    where TDto : class
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
        var entity = await _context.Set<TEntity>().FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task<PaginatedResult<TDto>> PaginateAsync(int page = 1, int rows = 20)
    {
        var query = _context.Set<TEntity>().AsQueryable();
        var totalCount = await query.CountAsync();
        var items = await query
            .Skip((page - 1) * rows)
            .Take(rows)
            .ProjectTo<TDto>(_mapper.ConfigurationProvider)
            .ToListAsync();
        return new PaginatedResult<TDto>
        {
            Items = items,
            TotalCount = totalCount,
            Page = page,
            Rows = rows
        };
    }

    public virtual async Task<TDto> CreateAsync(TDto item)
    {
        var entity = _mapper.Map<TEntity>(item);
        _context.Set<TEntity>().Add(entity);
        await _context.SaveChangesAsync();
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task<TDto> UpdateAsync(TKey id, TDto item)
    {
        var entity = await _context.Set<TEntity>().FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        _mapper.Map(item, entity);
        await _context.SaveChangesAsync();
        return _mapper.Map<TDto>(entity);
    }

    public virtual async Task DeleteAsync(TKey id)
    {
        var entity = await _context.Set<TEntity>().FindAsync(id);
        if (entity == null)
            throw new KeyNotFoundException($"{typeof(TEntity).Name} with id {id} not found");
        _context.Set<TEntity>().Remove(entity);
        await _context.SaveChangesAsync();
    }
}
"""