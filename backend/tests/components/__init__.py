"""Component tests hit the API or MCP "from the outside" directly but should not
need to be connected to the internet: the use containerized dependencies when possible or
mock external http calls when needed"""
