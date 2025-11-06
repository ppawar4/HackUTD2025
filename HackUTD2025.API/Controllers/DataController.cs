using HackUTD2025.API.Dtos;
using Microsoft.AspNetCore.Mvc;

namespace HackUTD2025.API.Controllers;

[Route("api/[controller]")]
public class DataController : ControllerBase
{
    private readonly ILogger<DataController> _logger;
    private readonly IEnumerable<HistoricalDataDto> _historicalDataDtos;
    private readonly HistoricalDataMetadataDto _historicalDataMetadataDto;

    public DataController(ILogger<DataController> logger, 
        IEnumerable<HistoricalDataDto> data,
        HistoricalDataMetadataDto metadata)
    {
        _logger = logger;
        _historicalDataDtos = data;
        _historicalDataMetadataDto = metadata;
    }

    [HttpGet]
    public IEnumerable<HistoricalDataDto> Get([FromQuery(Name = "start_date")] long? start, [FromQuery(Name = "end_date")] long? end)
    {
        DateTimeOffset? startTime = null;
        if (start.HasValue)
            startTime = DateTimeOffset.FromUnixTimeSeconds(start.Value);

        DateTimeOffset? endTime = null;
        if (end.HasValue)
            endTime = DateTimeOffset.FromUnixTimeSeconds(end.Value);

        var data = _historicalDataDtos;
        
        if (startTime is not null)
            data = data.Where(dto => dto.timestamp >= startTime);
        
        if (endTime is not null)
            data = data.Where(dto => dto.timestamp <= endTime);

        data.TryGetNonEnumeratedCount(out var count);
        
        return data;
    }
    
    [Route("metadata")]
    [HttpGet]
    public HistoricalDataMetadataDto GetMetadata() => _historicalDataMetadataDto;
}