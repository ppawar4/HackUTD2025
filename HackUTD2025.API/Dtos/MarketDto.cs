namespace HackUTD2025.API.Dtos;

public sealed record MarketDto(
    string id, string name, double latitude, double longitude, string description) : NodeDto(id, name, latitude, longitude);