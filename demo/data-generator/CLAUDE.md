# Calendar Event Extractor Demo Data Generator

## How to Run

### Using Claude Code (Recommended)
```bash
cd demo/data-generator
claude-code
```
Then ask: "Run the data generator script"

Claude Code will automatically read this CLAUDE.md file and know how to run everything correctly.

### Manual Run
```bash
cd demo/data-generator
source venv/bin/activate
python generate_calendar_demo.py
```

Note: Running the script multiple times will add more data (it doesn't clear existing data).

## What Data is Generated

The script generates **metadata only** for a calendar event extractor agent - no actual completion content:

- **Cost per request**: Varying from $0.002 to $0.08
- **Latency/Duration**: Response times with realistic P50/P95/P99 distributions
- **Volume**: 60-100 requests on weekdays, 15-30 on weekends
- **Time period**: Last 30 days of data
- **Success rate**: ~95% successful, 5% errors

## Example Charts to Create

After running the script, ask Claude to create these charts:

1. **Daily Cost Totals**: "Create a chart showing how much the calendar-event-extractor agent costs per day"
2. **P99 Latency Trend**: "Create a chart showing response time trends for the calendar extractor over the past month"
3. **Performance Table**: "Show me a breakdown of daily performance metrics for the calendar agent"

Perfect for demonstrating cost monitoring, performance tracking, and usage analytics.