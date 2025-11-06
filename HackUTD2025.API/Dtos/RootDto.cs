namespace HackUTD2025.API.Dtos;

public sealed record RootDto(
    List<CauldronDto> cauldrons,
    MarketDto enchanted_market,
    List<CourierDto> couriers,
    NetworkDto network);