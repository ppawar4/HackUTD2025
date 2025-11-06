namespace HackUTD2025.API.Dtos;

public sealed record NetworkDto(
    List<EdgeDto> edges, string description);