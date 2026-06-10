---
name: rss-weekly-reporter
description: Use when the user wants a weekly research report, literature digest, RSS paper screening, or latest_results.json analysis based on the maintained user research profile.
---

# RSS Weekly Reporter

## Overview

Generate a weekly research report from Academic Feed Manager output, usually `storage/latest_results.json`. The report is a screening tool based only on RSS metadata, especially title, authors, and abstract. Its purpose is to identify which new papers the user should consider opening and reading later, not to summarize full-text findings.

## Inputs

- RSS data: Default input is `storage/latest_results.json` in `/home/liyujun/projects/academic-feed-manager`. If the user gives a different run archive, use that file instead. 
- User research profile: read `references/user-research-profile.md` before screening. Treat it as read-only unless the user explicitly asks to update the maintained profile.
- Metadata fields: use `title`, `authors`, `abstract`, `source`, `url`, `doi`, and `published` only for identification and evidence.

## Workflow

1. Read the maintained research profile.
2. Read the RSS JSON and inspect run metadata, paper count, and available fields.
3. Screen papers semantically against the profile. Do not rely on exact keyword matching.
4. If there are many papers, batch them and keep a shortlist per batch.
5. If batched, merge shortlists, remove duplicates, and classify candidates using the selection tiers below.
6. Check coverage against the report structure and profile before writing.
7. Write a concise Markdown report.

## Selection Rules

1. Classify candidates before writing:
	- Tier 1: Direct profile hit. Include unless metadata is unusable.
	- Tier 2: Concrete transfer hit. Include when title or abstract shows a clear method, data, modeling, or evaluation bridge to the profile.
	- Tier 3: Interesting but remote. Usually omit. If included, keep it short, mark low confidence, and place it under the surprising or follow-up section.
2. Do not let a remote but interesting paper displace a direct profile hit. When two papers are equally relevant, prefer the one with clearer RSS evidence.
3. If a section has no strong hit, say that directly instead of filling it with weak papers.
4. Include adjacent or unexpected papers only when the title or abstract shows a real bridge to the user's research. Avoid broad analogies where the connection depends on saying that an abstract method "resembles" a latent state, diagnosis, or measurement problem. If the bridge requires more than two inference steps, omit it or keep it as a low-confidence follow-up note.

## Evidence Boundary

1. Treat the report as title/abstract triage. Do not fabricate details beyond RSS metadata, and do not claim what the full paper proves.
2. For each reason, make the evidence level explicit:
	- Use "题名直接显示..." when only the title supports the match.
	- Use "RSS 摘要显示..." when the abstract supports the match.
	- Use "可能迁移到..." only when the transfer path is concrete.
3. If metadata is thin but the title directly names a core profile construct, keep the paper and write conservatively: state that the match is title-based, avoid mechanism-level claims, and use confidence for topical relevance rather than proven usefulness.

## Report Format

Use these sections by default unless the user asks for a different structure:

```markdown
# Weekly Research Report - [run_id or date]

## 我最关心的问题是否有新的研究进展

## 我正在做的研究是否有新的研究进展

## 我感兴趣领域的新进展

## 值得特别注意的论文

## 本周建议跟进
```

Derive subsection names from the maintained profile's current research lines and ongoing projects. 

Default report length should be concise: target 12-18 papers total. If the run is unusually rich, exceed this only for clearly high-value papers.

- Main research-question sections: usually 3-6 papers each.
- Surprising or adjacent section: usually 2-4 papers.
- Follow-up section: short action list, not another full paper list.

Each included paper should have:
- one compact identification line: title, source/journal, URL
- one reason line: evidence cue plus profile bridge
- one confidence line: `high`, `medium`, or `low`

Include authors, date, or DOI only when they help identify or prioritize the paper. The reason and evidence boundary matter more than a long metadata block.

## Output Style

Use Chinese. Keep prose direct and evidence-based. Avoid generic phrases like "值得关注" unless followed by a specific reason.

Good reason:
> 这篇文章把 measurement/latent trait 的问题和 LLM 表征联系起来，可能启发 CDM 中属性掌握模式的表征学习。

Weak reason:
> 这篇文章和人工智能有关，值得关注。
