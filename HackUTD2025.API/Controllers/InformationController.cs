using HackUTD2025.API.Dtos;
using HackUTD2025.API.Utilities;

using Microsoft.AspNetCore.Mvc;

namespace HackUTD2025.API.Controllers;

[Route("api/[controller]")]
public class InformationController : ControllerBase
{
    private readonly ILogger<InformationController> _logger;
    private readonly NetworkDto _networkDto;
    private readonly MarketDto _marketDto;
    private readonly IEnumerable<CourierDto> _couriers;
    private readonly IEnumerable<CauldronDto> _cauldrons;
    private readonly NodeGraph _graph;

    public InformationController(ILogger<InformationController> logger, 
        NetworkDto network,
        MarketDto market,
        IEnumerable<CourierDto> couriers,
        IEnumerable<CauldronDto> cauldrons,
         NodeGraph graph)
    {
        _logger = logger;
        _networkDto = network;
        _marketDto = market;
        _couriers = couriers;
        _cauldrons = cauldrons;
        _graph = graph;
    }
    
    [Route("network")]
    [HttpGet]
    public NetworkDto GetNetwork() => _networkDto;
    
    [Route("market")]
    [HttpGet]
    public MarketDto GetMarket() => _marketDto;

    [Route("couriers")]
    [HttpGet]
    public IEnumerable<CourierDto> GetCouriers() => _couriers;
    
    [Route("cauldrons")]
    [HttpGet]
    public IEnumerable<CauldronDto> GetCauldrons() => _cauldrons;

    [Route("graph/neighbors/{nodeId}")]
    [HttpGet]
    public IEnumerable<NeighborDto> GetUndirectedNeighbors(string nodeId) => _graph.UndirectedNeighbords(nodeId);

    [Route("graph/neighbors/directed/{nodeId}")]
    [HttpGet]
    public IEnumerable<NeighborDto> GetNeighbors(string nodeId) => _graph.Neighbors(nodeId);
}