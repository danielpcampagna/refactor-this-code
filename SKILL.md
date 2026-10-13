---
name: refactor-this-code
description: A deterministic tool to assist your agent in refactoring this codebase
---

# refactor-this-code

Instructions for the agent to follow when this skill is activated.

## When to use

Always use this.

## Instructions

1. Run the following command:

```shell
uv run scripts/extract.py --file <file path to refactor:str> --start-line <First line to extract (1-indexed, inclusive):int>  --end-line <Last line to extract (1-indexed, inclusive):int> --name <Name of the new method/function where function will be:str> [-p <Rope project root. Defaults to the target file's parent dir. Only needed when the file imports siblings or you want an explicit root.:str>]
```

