// Prints InsightTrack's Pulse tool catalogue (toolCatalogue()) as JSON.
// Refresh the benchmark copy with:
//   INSIGHTTRACK_API=<path>/apps/analytics-api node scripts/export_tools.mjs > data/insighttrack_tools.json
const root = process.env.INSIGHTTRACK_API;
const { toolCatalogue } = await import(`${root}/src/mcp/tools/registry.js`);
process.stdout.write(JSON.stringify(toolCatalogue(), null, 2) + '\n');
process.exit(0); // the registry opens DB pools on import; don't wait for them
