# Multi-stage build: the SDK never ends up in the final image.
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY VehicleApi.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /out --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_HTTP_PORTS=8080 \
    DOTNET_EnableDiagnostics=0
EXPOSE 8080
# Non-root user provided by the Microsoft image (compatible with PSS "restricted").
USER $APP_UID
ENTRYPOINT ["dotnet", "VehicleApi.dll"]
