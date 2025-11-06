using System.Text.Json.Serialization;

namespace HackUTD2025.API.Dtos;

public class TicketsDto  
{
    [JsonPropertyName("metadata")]
    public TicketMetadataDto ticketMetadataDto { get; set; }
    public TicketDto[] transport_tickets { get; set; }
}