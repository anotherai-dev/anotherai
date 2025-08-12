# Calendar Event Extraction Agent - Debug Demo

This demo showcases how to use AnotherAI's playground tool to create completions for debugging AI agents.

## Purpose

The goal is to demonstrate:
1. How to use the playground tool to generate a completion
2. How to share the completion ID with Claude for debugging analysis
3. How Claude can identify and debug issues like missing timezone information

## Creating a Test Completion with a Problematic Input

Use the following playground command to generate a completion that will have issues to debug:

```python
mcp__anotherai__playground(
    agent_id="calendar-event-extractor", 
    models="gpt-4o-mini-latest",
    prompts=[[
        {
            "role": "system", 
            "content": "You are a calendar event extraction assistant. Extract all calendar events from emails, including dates, times with timezone, locations, and participants."
        },
        {
            "role": "user", 
            "content": "Extract calendar events from this email:\n\n{{email_content}}"
        }
    ]],
    output_schemas=[
        {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title or purpose of the event"
                            },
                            "date": {
                                "type": "string",
                                "description": "The date of the event"
                            },
                            "time": {
                                "type": "string",
                                "description": "The time of the event"
                            },
                            "timezone": {
                                "type": "string",
                                "description": "The timezone for the event"
                            },
                            "location": {
                                "type": "string",
                                "description": "Where the event takes place"
                            },
                            "participants": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "List of participants"
                            },
                            "notes": {
                                "type": "string",
                                "description": "Additional notes about the event"
                            }
                        },
                        "required": ["title", "date", "time", "timezone", "location", "participants"]
                    }
                }
            },
            "required": ["events"]
        }
    ],
    inputs=[
        {
            "variables": {
                "email_content": "Hi team,\n\nJust a reminder that we have our quarterly planning meeting tomorrow at 2:30pm in Conference Room B. Sarah from product, Mike from engineering, and Lisa from design will be presenting their roadmaps.\n\nAlso, don't forget the team lunch on Friday at noon at that new Italian place downtown.\n\nThanks,\nJohn"
            }
        }
    ],
    experiment_title="Calendar Event Extractor - Timezone Debug Demo",
    experiment_description="Testing calendar event extraction with structured outputs when timezone information is missing",
    author_name="Debug Demo"
)
```

## Getting the Completion for Debugging

After running the playground command:
1. The tool returns a completion ID (e.g., `01989f10-0eda-72b5-9c6d-fe9c470b218d`)
2. Share this completion with the user for debugging: `anotherai/completion/01989f10-0eda-72b5-9c6d-fe9c470b218d`
3. The user can then ask Claude to analyze this specific completion
4. Notice how the AI handles the missing timezone information in the output

## The Issue to Debug

When reviewing the completion with structured outputs, you'll notice:

### **Missing Timezone Information**
- The email mentions "2:30pm" and "noon" but provides no timezone
- The structured output **requires** a timezone field (it's in the required array)
- The AI is forced to either:
  - Make an assumption (which could be wrong)
  - Provide an empty string (which violates the schema intent)
  - Invent a timezone (potentially misleading)

This is a perfect debugging scenario because:
- It's a real-world problem (emails often lack timezone info)
- The structured output requirement creates a conflict
- The AI literally cannot know the correct answer
- It demonstrates the need for better schema design and prompt engineering

## Debugging Workflow

1. **Run the playground command** to create a completion
2. **Get the completion ID** from the tool response
3. **Share with the user**: `anotherai/completion/{completion_id}`
4. **User asks Claude to debug**: "Why does this completion not handle timezone correctly? anotherai/completion/01989f10-0eda-72b5-9c6d-fe9c470b218d"
5. **Claude analyzes the issue**: Reviews the completion and identifies the timezone problem
6. **Consider solutions**:
   - Update the prompt to handle missing timezones gracefully
   - Add instructions to flag when information is missing
   - Request timezone from the user when not specified

## Example: Creating an Improved Version

After identifying the timezone issue, you could create an improved prompt with better structured output handling:

```python
mcp__anotherai__playground(
    agent_id="calendar-event-extractor",
    models="gpt-4o-mini-latest",
    prompts=[[
        {
            "role": "system",
            "content": "You are a calendar event extraction assistant. Extract all calendar events from emails. When timezone is not specified, use 'UNKNOWN' and add a warning in the notes field."
        },
        {
            "role": "user",
            "content": "Extract calendar events from this email:\n\n{{email_content}}"
        }
    ]],
    output_schemas=[
        {
            "type": "object",
            "properties": {
                "events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "date": {"type": "string"},
                            "time": {"type": "string"},
                            "timezone": {
                                "type": "string",
                                "enum": ["UTC", "EST", "CST", "MST", "PST", "EDT", "CDT", "MDT", "PDT", "UNKNOWN"],
                                "description": "Use UNKNOWN when not specified"
                            },
                            "location": {"type": "string"},
                            "participants": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "notes": {"type": "string"},
                            "warnings": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Any missing or ambiguous information"
                            }
                        },
                        "required": ["title", "date", "time", "timezone", "location", "participants", "warnings"]
                    }
                }
            },
            "required": ["events"]
        }
    ],
    inputs=[
        {
            "variables": {
                "email_content": "Hi team,\n\nJust a reminder that we have our quarterly planning meeting tomorrow at 2:30pm in Conference Room B. Sarah from product, Mike from engineering, and Lisa from design will be presenting their roadmaps.\n\nAlso, don't forget the team lunch on Friday at noon at that new Italian place downtown.\n\nThanks,\nJohn"
            }
        }
    ],
    experiment_title="Calendar Extractor - Improved Timezone Handling",
    experiment_description="Improved version with enum for timezone field and warnings array for missing information",
    author_name="Debug Demo"
)
```

This demonstrates how debugging helps identify real issues and leads to better agent design.