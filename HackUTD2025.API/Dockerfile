FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
USER $APP_UID
WORKDIR /app
ENV ASPNETCORE_URLS="http://+:8080"
EXPOSE 8080

ENV TZ=America/Chicago

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src
COPY ["HackUTD2025.API/HackUTD2025.API.csproj", "HackUTD2025.API/"]
RUN dotnet restore "HackUTD2025.API/HackUTD2025.API.csproj.csproj"
COPY . .
WORKDIR "/src/WebApplication1"
RUN dotnet build "./HackUTD2025.API.csproj" -c $BUILD_CONFIGURATION -o /app/build

FROM build AS publish
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "./HackUTD2025.API.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "HackUTD2025.API.dll"]
