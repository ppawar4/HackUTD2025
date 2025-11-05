FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
USER $APP_UID
WORKDIR /app

ENV TZ=America/Chicago

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src
COPY ["HackUTD2025.API.csproj", "./"]
RUN dotnet restore "HackUTD2025.API.csproj"
COPY . .
WORKDIR "/src"
RUN dotnet build "HackUTD2025.API.csproj" -c $BUILD_CONFIGURATION -o /app/build

FROM build AS publish
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "HackUTD2025.API.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

ENV DOTNET_EnableDiagnostics=0
ENTRYPOINT ["sh", "-c", "export ASPNETCORE_URLS=\"http://0.0.0.0:${PORT}\" && exec dotnet HackUTD2025.API.dll"]