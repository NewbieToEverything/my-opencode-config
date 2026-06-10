---
name: rss-weekly-reporter
description: Use when the user wants a weekly research report, literature digest, RSS paper synthesis, or latest_results.json analysis for quantitative psychology, psychometrics, SEM, IRT, CDM, aberrant response detection, missing data, effect size/power analysis, depression/suicide prediction, or AI/ML/LLM transfer ideas.
---

# RSS Weekly Reporter

## Overview

Generate a weekly research report from Academic Feed Manager output, usually `storage/latest_results.json`. The report is a screening tool based only on RSS metadata, especially title, authors, and abstract. Its purpose is to identify which new papers the user should consider opening and reading later, not to summarize full-text findings.

## Inputs

Default input is `storage/latest_results.json` in `/home/liyujun/projects/academic-feed-manager`.

If the user gives a different run archive, use that file instead. If the user asks for the latest completed run and `latest_results.json` exists, use it directly. Do not run full RSS verification or fetch new publisher data unless the user explicitly asks and names target journals.

Use the model's semantic judgment directly. Do not rely on a fixed keyword list: the user's interests are nuanced, and good matches may be phrased in unexpected ways. If the JSON contains many papers, process papers in batches using title, authors, abstract, source, URL, and date, then merge the strongest candidates across batches.

## User Research Profile

Read `references/user-research-profile.md` before writing the report. This is the only maintained research-interest profile. If the user's interests change, update that natural-language file rather than creating keyword lists.

Core areas:
- Quantitative psychology / psychometrics.
- SEM: especially exploratory factor analysis and estimating the number of factors.
- IRT/CDM: aberrant response detection, person fit, item fit, change point analysis, mixture modeling, careless/rapid/random responding, cheating, item leakage/preknowledge.
- CDM as current center: estimating number of attributes, attribute hierarchy, Q-matrix calibration, reducing practitioner burden, longitudinal cognitive diagnosis, knowledge tracing, HMM/time-series/LSTM models, and learning material recommendation with reinforcement learning.
- Current projects: multilevel missing data, ANOVA effect size formula differences and power analysis, LLM prediction of depression and suicidal behavior.
- Transfer interests: AI, machine learning, reinforcement learning, LLMs, transformers, and methods that can be moved into the above research lines.

## Report Structure

Write the weekly report in Markdown with exactly these sections:

```markdown
# Weekly Research Report - [run_id or date]

## 1. 我最关心的问题是否有新的研究进展

## 2. 我正在做的 research 是否有新的研究进展

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

## Ranking Heuristics

Prioritize papers with explicit overlap between psychometrics/quantitative methods and modern AI/ML. A paper like the Nature Machine Intelligence example combining psychometrics/measurement with LLMs should be treated as high priority even if it is outside the user's usual journal list. The report should only say that title/abstract metadata makes it look relevant; it should not claim what the full paper proves.

High priority signals:
- Terms related to CDM, IRT, SEM, factor number, factor analysis, Q-matrix, attribute hierarchy, knowledge tracing, longitudinal diagnosis, person fit, item fit, aberrant response, response time, cheating, item leakage, mixture model, change point.
- Current project terms: multilevel, hierarchical data, missing data, imputation, ANOVA, effect size, power analysis, depression, suicide, mental health prediction.
- Transfer terms: LLM, language model, transformer, representation learning, reinforcement learning, knowledge tracing, graph neural network, sequence model, anomaly detection, foundation model.
- Publication venue is broad or adjacent but high-quality, especially Nature family, Science family, PNAS, psychometrics/statistics/education measurement venues, ML venues, or cognitive science venues.

Medium priority signals:
- General statistical methodology that could plausibly transfer.
- AI/ML papers with clear measurement, diagnosis, longitudinal, educational, or psychological data implications.

Low priority signals:
- Generic AI benchmark papers without measurement, diagnosis, education, psychology, missing-data, or mental-health relevance.

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
