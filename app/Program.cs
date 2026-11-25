// Demo "vehicle positions" API (inspired by GTFS-Realtime).
//  GET  /healthz                     -> health probe
//  GET  /api/v1/vehicles             -> positions snapshot (Redis cache-aside, 10 s TTL)
//  POST /api/v1/vehicles/positions   -> publishes a position to Pub/Sub (ordering key = vehicleId)
// Dependencies are optional: without REDIS_HOST / PUBSUB_TOPIC, the API runs in degraded mode.

using System.Text.Json;
using Google.Cloud.PubSub.V1;
using Google.Protobuf;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
var cfg = builder.Configuration;

var redisHost = cfg["REDIS_HOST"];
IConnectionMultiplexer? redis = null;
if (!string.IsNullOrWhiteSpace(redisHost))
{
    var options = ConfigurationOptions.Parse($"{redisHost}:{cfg["REDIS_PORT"] ?? "6379"}");
    options.AbortOnConnectFail = false; // don't crash if Redis is unavailable at startup
    options.ConnectTimeout = 2000;
    redis = ConnectionMultiplexer.Connect(options);
}

PublisherClient? publisher = null;
var projectId = cfg["GCP_PROJECT_ID"];
var topicId = cfg["PUBSUB_TOPIC"];
if (!string.IsNullOrWhiteSpace(projectId) && !string.IsNullOrWhiteSpace(topicId))
{
    publisher = await new PublisherClientBuilder
    {
        TopicName = TopicName.FromProjectTopic(projectId, topicId),
        Settings = new PublisherClient.Settings { EnableMessageOrdering = true },
    }.BuildAsync();
}

var app = builder.Build();

app.MapGet("/healthz", () => Results.Ok(new { status = "ok" }));

app.MapGet("/api/v1/vehicles", async () =>
{
    const string cacheKey = "vehicles:snapshot";
    var db = redis?.IsConnected == true ? redis.GetDatabase() : null;

    if (db is not null)
    {
        var cached = await db.StringGetAsync(cacheKey);
        if (cached.HasValue)
            return Results.Text(cached.ToString(), "application/json");
    }

    // Simulated data: in reality, read from the GTFS-RT feed or the database.
    var snapshot = JsonSerializer.Serialize(new
    {
        generatedAt = DateTimeOffset.UtcNow,
        source = db is null ? "origin-no-cache" : "origin",
        vehicles = Enumerable.Range(1, 5).Select(i => new
        {
            vehicleId = $"BUS-{100 + i}",
            routeId = (i * 10 + 50).ToString(),
            lat = 45.50 + Random.Shared.NextDouble() / 20,
            lon = -73.57 + Random.Shared.NextDouble() / 20,
        }),
    });

    if (db is not null)
        await db.StringSetAsync(cacheKey, snapshot, TimeSpan.FromSeconds(10));

    return Results.Text(snapshot, "application/json");
});

app.MapPost("/api/v1/vehicles/positions", async (VehiclePosition position) =>
{
    if (publisher is null)
        return Results.Problem("Pub/Sub not configured", statusCode: 503);

    var message = new PubsubMessage
    {
        Data = ByteString.CopyFromUtf8(JsonSerializer.Serialize(position)),
        OrderingKey = position.VehicleId, // ordering guaranteed per vehicle
        Attributes = { ["schema"] = "vehicle-position.v1" },
    };
    var messageId = await publisher.PublishAsync(message);
    return Results.Accepted(value: new { messageId });
});

// Graceful shutdown: flush the Pub/Sub buffer before the pod terminates (SIGTERM).
app.Lifetime.ApplicationStopping.Register(() =>
    publisher?.ShutdownAsync(TimeSpan.FromSeconds(10)).GetAwaiter().GetResult());

app.Run();

record VehiclePosition(string VehicleId, string RouteId, double Lat, double Lon, DateTimeOffset Timestamp);
