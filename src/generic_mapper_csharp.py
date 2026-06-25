GENERIC_MAPPER_CSHARP = """\
using AutoMapper;
using $$config_model_path$$;
using $$config_dto_path$$;

namespace $$config_mapper_path$$;

public class GenericMappingProfile<TEntity, TDto> : Profile
    where TEntity : class
    where TDto : class
{
    public GenericMappingProfile()
    {
        CreateMap<TEntity, TDto>().ReverseMap();
    }
}
"""

GENERIC_MAPPER_TEMPLATE_CSHARP = """\
using AutoMapper;
using $$config_model_path$$;
using $$config_dto_path$$;

namespace $$config_mapper_path$$;

public class $$Entity$$MappingProfile : Profile
{
    public $$Entity$$MappingProfile()
    {
        CreateMap<$$TRequestDto$$, $$Entity$$>();
        CreateMap<$$Entity$$, $$TResponseDto$$>();
        CreateMap<$$Entity$$, $$TResponseDto$$Simplified>();
    }
}
"""
