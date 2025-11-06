namespace HackUTD2025.API.Dtos;

public class TicketMetadataDto
{
    public int total_tickets { get; set; }
    public int suspicious_tickets { get; set; }
    public string start { get; set; }
    public string end { get; set; }
}