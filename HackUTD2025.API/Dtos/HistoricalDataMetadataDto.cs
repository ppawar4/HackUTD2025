namespace HackUTD2025.API.Dtos;

public class HistoricalDataMetadataDto
{
    public string start_date { get; set; }
    public string end_date { get; set; }
    public int interval_minutes { get; set; }
    public string unit { get; set; }
}