namespace HackUTD2025.API.Dtos;

public sealed record EdgeDto(
    string from, string to, int travel_time_minutes);