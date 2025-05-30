---
trigger: always_on
---

// Rule definitions for Windsurf
  "rules": [
    {
      "name": "BrowserTesting",
      "match": {
        // Triggers when tasks involve browser rendering or console logs
        "intent": ["run in browser", "browser test", "console log"]
      },
      "action": {
        // Route these tasks to the Puppeteer MCP server
        "use_mcp": "puppeteer-mcp"
      }
    },
    {
      "name": "GenerateUnitTests",
      "match": {
        // Apply when new functions are created
        "pattern": "function ",
        "language": "javascript"
      },
      "action": {
        // Instruct model to scaffold corresponding unit tests
        "generate_tests": true
      }
    },
    {
      "name": "LintAndFormat",
      "match": {},
      "action": {
        // Always run linting and formatting checks
        "run_linters": ["eslint", "prettier"]
      }
    },
    {
      "name": "DefaultMCP",
      "match": {},
      "action": {
        // Fallback for all other code tasks
        "use_mcp": "context7"
      }
    }
  ]