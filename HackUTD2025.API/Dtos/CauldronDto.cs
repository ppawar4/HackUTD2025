namespace HackUTD2025.API.Dtos;

public sealed record CauldronDto(
    string id, string name, double latitude, double longitude, int max_volume) : NodeDto(id, name, latitude, longitude);