---
name: rss-weekly-reporter
description: Use when the user wants a weekly research report, literature digest, RSS paper synthesis, or latest_results.json analysis for quantitative psychology, psychometrics, SEM, IRT, CDM, aberrant response detection, missing data, effect size/power analysis, depression/suicide prediction, or AI/ML/LLM transfer ideas.
---

# RSS Weekly Reporter

## Overview

Generate a weekly research report from Academic Feed Manager output, usually `storage/latest_results.json`. The report is a screening tool based only on RSS metadata, especially title, authors, and abstract. Its purpose is to identify which new papers the user should consider opening and reading later, not to summarize full-text findings.

## Inputs

- RSS data: Default input is `storage/latest_results.json` in `/home/liyujun/projects/academic-feed-manager`. If the user gives a different run archive, use that file instead. If the user asks for the latest completed run and `latest_results.json` exists, use it directly.
- Fetching boundary: do not run full RSS verification or fetch new publisher data unless the user explicitly asks and names target journals.
- User research profile: read `references/user-research-profile.md` before writing the report. This is the only maintained research-interest profile. If the user's interests change, update that natural-language file rather than creating keyword lists.
- Screening method: filter papers based on the profile using the model's semantic judgment. If the JSON contains many papers, process papers in batches using title, authors, abstract, source, URL, and date, then merge the strongest candidates across batches.

## Report Structure

Write the weekly report in Markdown. Use these sections by default unless the user asks for a different structure:

```markdown
# Weekly Research Report - [run_id or date]

## 1. 我最关心的问题是否有新的研究进展

## 2. 我正在做的研究是否有新的研究进展

## 3. 我感兴趣领域的新进展，以及可迁移到我研究中的思路

## 值得特别注意但容易漏看的论文

## 本周建议跟进
```

Each paper entry should include:
- title
- source/journal
- URL
- why it may matter, tied to a specific user research line and explicitly based on title/abstract evidence
- confidence: `high`, `medium`, or `low`

Do not overclaim. Treat the report as title/abstract triage. Do not infer methods, datasets, results, or claims that are not visible in the RSS metadata.

## Ranking Principles

Prioritize papers by semantic fit to the research profile, not by matching a keyword list. A strong candidate should satisfy at least one of these conditions:

- It directly addresses a core research line, current project, or transfer interest in the profile.
- It offers a method, modeling idea, dataset type, or evaluation perspective that could plausibly migrate into the user's research.
- It bridges measurement, psychometrics, psychology, education, or mental health with modern AI/ML in a way the user might miss during routine journal scanning.

The report should only say that title/abstract metadata makes a paper look relevant. Do not claim what the full paper proves.

## Screening Discipline

1. Start from RSS metadata in the JSON: `title`, `authors`, `abstract`, plus `source`, `url`, `doi`, and `published` only for identification.
2. Read title and abstract semantically against the research profile; do not treat exact keyword matching as the main criterion.
3. If there are many papers, batch them and keep a shortlist per batch:
   - direct hits for SEM/IRT/CDM/current projects
   - AI/ML/LLM papers with a clear transfer path
   - surprising adjacent papers that the user might otherwise miss
4. Merge the batch shortlists, remove duplicates, and group candidates by the three report questions rather than by journal.
5. Keep weak matches out of the main sections unless they offer a concrete transfer idea.
6. Include a "surprising but relevant" paper when it bridges domains, even if it does not mention SEM/IRT/CDM directly.
7. Prefer fewer, better annotated papers over a long undifferentiated list.

## Output Style

Use Chinese. Keep prose direct and evidence-based. Avoid generic phrases like "值得关注" unless followed by a specific reason.

Good reason:
> 这篇文章把 measurement/latent trait 的问题和 LLM 表征联系起来，可能启发 CDM 中属性掌握模式的表征学习。

Weak reason:
> 这篇文章和人工智能有关，值得关注。

## Follow-Up

If the report reveals a paper that looks highly relevant but RSS metadata is thin, list it under `本周建议跟进` with the action: open paper page or retrieve the full text later. Do not fabricate details beyond the title/author/abstract metadata.
