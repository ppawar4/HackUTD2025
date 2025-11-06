using HackUTD2025.API.Dtos;

namespace HackUTD2025.API.Utilities;

public sealed class NodeGraph
{
    private readonly Dictionary<string, List<NeighborDto>> _adj =
        new(StringComparer.OrdinalIgnoreCase);

    private readonly Dictionary<string, List<NeighborDto>> _undAdj =
        new(StringComparer.OrdinalIgnoreCase);

    public NodeGraph(IEnumerable<NodeDto> nodes, IEnumerable<EdgeDto> edges)
    {
        foreach (var n in nodes)
        {
            _adj.TryAdd(n.id, new());
            _undAdj.TryAdd(n.id, new());
        }

        foreach (var e in edges)
        {
            AddToDirectedGraph(e);
            AddToUndirectedGraph(e);
        }
    }

    private void AddToDirectedGraph(EdgeDto e)
    {
        _adj.TryAdd(e.from, new());
        _adj[e.from].Add(new(e.to, TimeSpan.FromMinutes(e.travel_time_minutes)));
    }

    private void AddToUndirectedGraph(EdgeDto e)
    {
        _undAdj.TryAdd(e.from, new());
        _undAdj[e.from].Add(new(e.to, TimeSpan.FromMinutes(e.travel_time_minutes)));

        _undAdj.TryAdd(e.to, new());
        var rev = new NeighborDto(e.from, TimeSpan.FromMinutes(e.travel_time_minutes));
        if (!_undAdj[e.to].Contains(rev))
        {
            _undAdj[e.to].Add(rev);
        }
    }

    public IEnumerable<NeighborDto> Neighbors(string nodeId)
    {
        if (_adj.TryGetValue(nodeId, out var list))
            return list;
        return [];
    }

    public IEnumerable<NeighborDto> UndirectedNeighbords(string nodeId)
    {
        if (_undAdj.TryGetValue(nodeId, out var list))
            return list;
        return [];
    }
}