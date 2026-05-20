# Browser Automation Rules

## **ALWAYS** use the agent-browser skill

When the user requests searching, fetching, extracting data from, taking snapshot of, form automation or interacting with websites, invoke and use the agent-browser skill.  

## Curl/wbget as a fallback

**MUST** use curl/wget when agent-browser is not applicable (e.g., operation failed, CAPTCHA test failure, etc.). 

For the following websites, **MUST** use curl.

### GitHub.com

All GitHub operations (searching repositories, fetching issues, reading files, etc.) **MUST** use **AUTHENTICATED** curl calls:

```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/..."
```
