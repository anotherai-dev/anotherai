# AnotherAI vision

"Give your AI agents* better tools to build AI agents"
* we focus on Claude Code and Cursor. 

ALT: "Tools for Claude & Cursor* to build your AI agents"
* while we focus on Claude Code and Cursor, we are MCP compatible, so any MCP compatible vibe coding tool can be used.

Work is changing. AI agents are going to be performing work on your behalf.
We designed AnotherAI to be used by AI agents first. It's a complete reimagination of our previous project, WorkflowAI. Previously interfaces used to be important, now the focus is on exposing tools that your agent can use to achieve their goals.

Imagine you ask your AI coding assistant to build a simple agent that can [extract calendar events from an email]. In order to achieve that, your AI coding assistant needs to:
- be able to compare different prompts and models [demo]
- be able to know the cost of each model [demo]
- suggest a few versions of the agent and get your feedback [demo]
Then, once your agent is working, your AI coding assistant needs to be able to:
- review performance metrics (latency, cost) [demo]
- debug a specific situation where the agent is not working as expected [demo]
- deploy a fix to the agent [demo]
- compare how a new model performs compared to the production model [demo]

We've build tools that enable your AI coding assistant to do all of this.

The AI coding assistant is in the driver seat, and you are now a reviewer: giving feedback at specific points in the process. Instead of doing the work, you are writing the prompt for the AI coding assistant to do the work (sometimes for a few minutes).

But let's be honest, Claude Code or Cursor are already capable of writing the code, the prompt, connecting to an LLM API. So what's our role? [...] Our goal is to accelerate how long it will take your AI coding assistant to build you what you want, but without compromising on the customization that a full vibe-coding (writing all the code from scratch) would allow. We've expressed this in the principles below.

## Principles

1. **Agent-First Architecture**: Every feature is designed to be consumed by AI agents first, with human interfaces as a secondary consideration. This ensures maximum efficiency when Claude Code or Cursor are building on your behalf. 

2. **Never Get Stuck**: You can always access the underlying data in the way you want. Both our MCP and API let you run direct SQL queries against the database. If you need a visualization that we don't provide, you can always vibe code it. Coming soon: bring your own API keys for even more control.

3. **Compatible with Existing Code**: We built on top of the OpenAI chat completions API to maximize compatibility with existing code and SDKs. While we use the OpenAI API format, you're not limited to OpenAI models - we support 50+ models across multiple providers including Anthropic, Google, Mistral, and more. AnotherAI works with any programming language - Python, JavaScript, Go, Ruby, Java, C#, and more - since it's exposed as a standard API.

4. **Fully Managed**: We handle the infrastructure complexity - data storage, keeping LLM prices up-to-date, adding new models every week, maintaining the MCP server, and more. Focus on building your agents, not managing infrastructure.

## FAQ

**Q: Do you markup LLM costs?**
A: No. You pay the same price as going directly to the provider, while getting all the additional tooling and management benefits.

**Q: Will you open-source the codebase?**
A: Yes, we will open-source our codebase very soon.

**Q: Do you train on my data?**
A: No, we do not train on your data. Neither do the LLM providers.

**Q: What models do you currently support?**
A: [Placeholder: We support 50+ models across major providers including OpenAI, Anthropic, Google, Mistral, and more. Visit our documentation for the full list.]

**Q: Are you SOC2 compliant?**
A: Yes, we are SOC2 compliant. We take security and data privacy seriously.

[DEMO]
[use-case 1: create a new agent]
[use-case 2: migrate an existing agent]
[use-case 3: debug an agent]
[use-case 4: find a cheaper model for an existing agent]
[use-case 5: deploy a fix to an existing agent]
[use-case 6: ask a question about my agents]

Install our MCP server to get started: [CursorAI | Claude Code]
And start prompting..