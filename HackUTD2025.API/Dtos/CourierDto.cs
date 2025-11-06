namespace HackUTD2025.API.Dtos;

public sealed record CourierDto(
    string courier_id, string name, int max_carrying_capacity);