namespace HackUTD2025.API.Dtos;


public class HistoricalDataDto
{
    public DateTimeOffset timestamp { get; set; }
    public CauldronLevelsDto cauldron_levels { get; set; }
}
