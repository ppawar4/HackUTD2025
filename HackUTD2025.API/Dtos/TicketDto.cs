namespace HackUTD2025.API.Dtos;

public class TicketDto
{
    public string ticket_id { get; set; }
    public string cauldron_id { get; set; }
    public double amount_collected { get; set; }
    public string courier_id { get; set; }
    public string date { get; set; }
}