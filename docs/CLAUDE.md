# Documentation Guidelines

## Template Variables

The documentation uses template variables that are automatically replaced when the documentation is generated:

- `{{API_URL}}` - This is NOT an environment variable. It's a template placeholder that gets automatically replaced with the appropriate API endpoint URL when the documentation is rendered. Users will see the correct URL based on their deployment (cloud or self-hosted).

When writing documentation examples:

- Use `{{API_URL}}` as a placeholder for the AnotherAI API endpoint
- Do NOT treat it as an environment variable that users need to set
- The actual URL will be injected at documentation build/render time

Example usage in code blocks:

```python
client = AsyncOpenAI(
    base_url="{{API_URL}}/v1",  # This will be replaced with the actual URL
    api_key=os.environ.get("ANOTHERAI_API_KEY")
)
```
