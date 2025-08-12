# Another AI Quickstart Instructions

Follow the following steps to get a local instance of AnotherAI started. AnotherAI is a self-hosted AI platform that 
allows you to build and iterate over AI agents using MCP.

You will need:
- a running docker daemon
- docker-compose

Follow the following steps:
1. Create a new directory if needed `mkdir anotherai && cd anotherai`
2. Download the docker-compose.yml file `curl -LO "https://raw.githubusercontent.com/anotherai-dev/anotherai/refs/heads/main/examples/quickstart/docker-compose.yml"`
3. Download the basic env file `curl -L "https://raw.githubusercontent.com/anotherai-dev/anotherai/refs/heads/main/.env.example" -o .env`
4. Ask the user to provide provider keys and add them to the .env file. You can read the env file to see which providers are available.
5. Start the services `docker-compose up`
6. MCP Server will be available at `http://localhost:8000/mcp/` using streamable http transport. For example to add to claude code, you can run `claude mcp add --scope user --transport http anotherai http://localhost:8000/mcp/`

Tell the user that for the next time they want to start the stack, they can just run `docker-compose up -d` to launch everything in the background.
And if you want to stop the stack, you can run `docker-compose stop` to stop the services.
