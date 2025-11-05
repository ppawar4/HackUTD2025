using System.Text.Json;

using HackUTD2025.API.Dtos;

var builder = WebApplication.CreateBuilder(args);

var data = await ReadHistoricalDataAsync();
var metadata = await ReadMetadataAsync();
var dtos = await ReadDataAsync();
var tickets = await ReadTicketDataAsync();

var graph = new DirectedGraph([.. dtos.cauldrons, dtos.enchanted_market], dtos.network.edges);

builder.Services.AddSingleton(graph);
builder.Services.AddSingleton(tickets);

builder.Services.AddSingleton(dtos.network);
builder.Services.AddSingleton(dtos.enchanted_market);
builder.Services.AddSingleton<IEnumerable<CourierDto>>(dtos.couriers);
builder.Services.AddSingleton<IEnumerable<CauldronDto>>(dtos.cauldrons);

builder.Services.AddSingleton(metadata);
builder.Services.AddSingleton(data);

builder.Services.AddControllers();
builder.Services.AddOpenApi();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Configure the HTTP request pipeline.

app.MapOpenApi();
app.UseSwagger();
app.UseSwaggerUI(c => {
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "HackUTD2025.API V1");
});


app.UseRouting();

app.MapControllers();

app.Use((context, next) => {
    app.Logger.LogInformation("Received request: {Method} {Path}{Query}", context.Request.Method, context.Request.Path, context.Request.QueryString);
    return next();
});
app.UseResponseCaching();

app.Run();

async ValueTask<IEnumerable<HistoricalDataDto>> ReadHistoricalDataAsync()
{
    using StreamReader reader = new("Data/testhistorical_data 2.json");

    var data = await JsonSerializer.DeserializeAsync<IEnumerable<HistoricalDataDto>?>(reader.BaseStream);

    return data ?? throw new Exception("Where's our data???");
}

async ValueTask<HistoricalDataMetadataDto> ReadMetadataAsync()
{
    using StreamReader reader = new("Data/testhistorical_metadata.json");

    var data = await JsonSerializer.DeserializeAsync<HistoricalDataMetadataDto?>(reader.BaseStream);

    return data ?? throw new Exception("Where's our history metadata???");
}

async ValueTask<RootDto> ReadDataAsync()
{
    using StreamReader reader = new("Data/testcauldrons 2.json");

    var data = await JsonSerializer.DeserializeAsync<RootDto>(reader.BaseStream);

    return data ?? throw new Exception("Where's our cauldron data???");
}

async ValueTask<TicketsDto> ReadTicketDataAsync()
{
    using StreamReader reader = new("Data/testtransport_tickets-1 1.json");

    var data = await JsonSerializer.DeserializeAsync<TicketsDto>(reader.BaseStream);

    return data ?? throw new Exception("Where's our ticket data???");
}

