# AnotherAI: let Claude Code build other AI agents. [alpha]

Like you, we fell in love with Claude Code and Cursor. Watching the AI work for a few minutes, vibecoding anything you want using English, feels like magic.
It seems like all AI need are better tools to achieve even more.

**So what happens when we give Claude Code better tools to build AI agents?**
We've tried and the early results are promising. We wanted to share an early preview with you.

**DEMOs**

```
> Claude: can you build with AnotherAI an agent that can extract calendar events from 
> an email? Make sure to try 3 different models from OpenAI, Anthropic and Google, 
> and 5 different emails. Tell me what you think.
```

Watch the magic happen:

![New Agent](/docs/public/gifs/new-agent.gif)

Claude Code will:
- Understand how AnotherAI works by using the `search_documentation` tool
- Pick the models to try using `list_models` tool
- Use `playground` tool to compare the models
- Report back the results

And you can see the results in the web app:
![Experiment Compare Models](/docs/public/images/experiment-compare-models.png)

---

```
> Claude: can you try GPT-5 on 10 random completions from agent: 
> extract-calendar-events? what do you think?
```

Sit back and enjoy the show 🍿

![Demo GPT-5](/docs/public/gifs/demo-gpt5.gif)

---

```
> Claude: can you show me how much $ we're spending daily, by agent?
```

Claude will write the SQL query to create the view, and you can see the results in the web app:

![New View Cost Per Day Per Agent](/docs/public/gifs/new-view-cost-per-day-per-agent.gif)

![View Graph Cost Over Time](/docs/public/images/view-graph-cost-over-time.png)

---

```
> Claude: why is this anotherai/completion/01989ada-2185-739f-f5c2-7bb67faaad19 wrong?
> Can you help fix?
```

Claude will fetch the completions, and fix the issue most of the time!

> [!NOTE]
> This is an early release of AnotherAI. We do not recommend using it in production yet.

## How it works

AnotherAI has four main components:
1. An **OpenAI compatible API**, which is super great for compatibility with any programming language or SDKs, but that **supports all the models** and **logs all the completions**.
2. A **MCP server** that exposes tools designed specifically for Claude Code (and Cursor) to build agents, compare models/prompts (this concept is called experiments), debug issues using the logs, and getting insights from logs (ask any question in English you want).
3. A **simple web interface** to be able to review the work that the AI did in a nicer UX than a chat/terminal UI (for example comparing different prompts side-by-side), look at the [completions logs](/docs/public/images/completions-list.png), and [charts](/docs/public/images/view-graph-cost-over-time.png) that your AI prepared for you.
4. An **API** for everything else you want to build on top of AnotherAI, giving you a flexibility that we like when vibe-coding (custom evaluations like LLM-as-a-judge, querying the logs database directly, ..).

### OpenAI compatible API

Available at `http://localhost:8000/v1/chat/completions`, this API endpoint accepts any library that already uses OpenAI. To start using the endpoint, simply set the `base_url` to `http://localhost:8000/v1` on most OpenAI or OpenAI compatible SDKs.

```
> Claude: how many models from how many providers are supported by AnotherAI?
```

> Based on the data from AnotherAI's API, I can see that AnotherAI supports 95 models from 12 different providers: ...

The easiest way to get started is to ask Claude Code to setup AnotherAI on your agent. For example:

```
Claude: can you setup AnotherAI on this agent @my-agent.py?
```

### MCP server

We use the `http` transport to expose the MCP server at `http://localhost:8000/mcp/`. See below for [instructions](#mcp-setup) on how to install it in Claude Code and Cursor.

We have curated a list of tools that we think are useful for building AI agents, available at [`backend/protocol/api/_mcp.py`](blob/main/backend/protocol/api/_mcp.py). We've already spent a good amount of time to make sure these tools are well designed and documented for Claude Code.

### Web App

The web app is available at [http://localhost:3000/](http://localhost:3000/). 
Features:
- View experiments
- View completions logs
- View charts

The web app is designed to be read-only, and is used with Claude Code and Cursor. For example, to create a new view, use the following prompt in Claude Code:

```
> Claude: can you create a new view in Another that shows the average, p90 and p99 
> latency across all my agents? Make a line graph per day.
```

![New Chart](/docs/public/gifs/new-chart.gif)

```
> Claude: show me all the completions that are taking more than 10 seconds to 
> complete.
```

![New View](/docs/public/gifs/new-view.gif)

![Completions Slow List](/docs/public/images/completions-slow-list.png)

### API

The API auto-generated documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Try it out

### Self Host

First, you'll need to self-host your own AnotherAI. The easiest way is to ask Claude Code to do it for you.

> You can also just ask claude. 
> `claude "Please follow instructions in https://raw.githubusercontent.com/anotherai-dev/anotherai/refs/heads/main/examples/quickstart/INSTRUCTIONS.md"`

```sh
# Create a new directory
mkdir anotherai && cd anotherai
# Download the docker-compose.yml file
curl -LO "https://raw.githubusercontent.com/anotherai-dev/anotherai/refs/heads/main/examples/quickstart/docker-compose.yml"
# Download the basic env file
curl -L "https://raw.githubusercontent.com/anotherai-dev/anotherai/refs/heads/main/.env.example" -o .env
# Add your Provider API Keys to the .env file
# Start the service
docker-compose up
```

### MCP Setup

#### For Claude

To set up the MCP (Model Context Protocol) with Claude Code locally:

```sh
claude mcp add --scope user --transport http anotherai http://localhost:8000/mcp/
```

#### For Cursor

Tap on this button to install the MCP server in Cursor (make sure the MCP server is running see [#try-it-out](#try-it-out)):

<a href="cursor://anysphere.cursor-deeplink/mcp/install?name=anotherai&config=eyJ1cmwiOiJodHRwOi8vMTI3LjAuMC4xOjgwMDAvbWNwLyJ9"><img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Add anotherai MCP server to Cursor" height="32" /></a>

```mcp.json
{
  "mcpServers": {
    "anotherai": {
      "url": "http://127.0.0.1:8000/mcp/"
    }
  }
}
```

### Try out some prompts

After you have the above self-hosting configuration and MCP set up, now you can try it. Here are some sample prompts you can send to Claude Code to get you started:

```
> Create an experiment in AnotherAI that compares how GPT-5 mini and GPT-4 mini extract
> the sentiment from an input product review.
```

```
> Use AnotherAI to help me find the model that can summarize a long article the fastest.
```

```
> Use AnotherAI to test how clearly and accurately 5 different models can answer complex
> STEM questions.
```

If you have an existing agent in your codebase, here are some ways you can ask Claude Code to use AnotherAI to help you improve it:

```
> Use AnotherAI to help me find a cheaper model that still produces high quality
> outputs for [@agent-file].
```
```
> Propose improvements to [@agent-file] and create in experiment
> in AnotherAI that compares my current and the new prompt on the same model
```

### Join our community on Slack!

Please, come say hi! We're still in alpha, and we're happy to get your feedback. We're pretty sure some things won't work out of the box, but we can promise we'll try our best to fix things quickly. 

Here -> [anotherai-dev.slack.com](https://join.slack.com/t/anotherai-dev/shared_invite/zt-3av2prezr-Lz10~8o~rSRQE72m_PyIJA)

## FAQ

Once the MCP is installed, you can ask your questions directly via Claude Code or Cursor. The tool `search_documentation` is available.

> I have already an agent running, can I use AnotherAI to improve it?
> 
Yes, but you'll need to switch the existing agent to use our Chat Completions API. Ask Claude Code to do it for you.
We are considering adding an API endpoint that captures the completions after they have been generated, let us know if you'd like to see this feature.

> (your question here)

*(coming soon, based on your [questions](https://github.com/anotherai-dev/anotherai/discussions))*
