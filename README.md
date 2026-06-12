# Cold Outreach Recipient Intelligence

Research project studying what **recipients** of B2B cold outreach actually respond to, delete, and block — not what senders claim works.

## The Angle

Everyone studying cold outreach for B2B SaaS picks 10 LinkedIn sales coaches and collects their tips on writing better cold emails. That's the obvious move.

We inverted the problem. Instead of studying senders, we studied **recipients** — the founders, VPs, and HR leaders who receive cold outreach daily and have publicly documented what makes them delete, block, or occasionally reply.

This is called inversion: solve a problem by studying how to guarantee failure, then avoid it.

## Why This Matters for 100hires

100hires sells ATS software to SMB hiring managers and founders. Their product includes AI email composer, candidate outreach sequences, and deliverability tools.

The 10 experts in this research are not 100hires' users — they are **100hires' buyers**. This playbook is for 100hires' internal SDRs, mapping the exact deletion triggers and cognitive friction of the SMB founders and TA leaders they cold pitch daily.

## The 10 Experts

Deliberately avoided obvious sales coach names. Picked practitioners who receive outreach at scale and publicly document what works and what doesn't.

| Name | Role | LinkedIn | Why High-Signal |
|------|------|----------|-----------------|
| Peep Laja | CEO, Wynter / CXL | [linkedin.com/in/peeplaja](https://www.linkedin.com/in/peeplaja/) | Runs message-testing research; documents why pitches fail from the recipient side |
| Andrew Gazdecki | CEO, Acquire.com | [linkedin.com/in/agazdecki](https://www.linkedin.com/in/agazdecki/) | Founder inbox at scale; posts about what M&A outreach gets deleted |
| Mac Reddin | CEO, Commsor | [linkedin.com/in/macreddin](https://www.linkedin.com/in/macreddin/) | Community-led founder; vocal about bad vendor and recruiter DMs |
| Dave Gerhardt | Founder, Exit Five | [linkedin.com/in/davegerhardt](https://www.linkedin.com/in/davegerhardt/) | B2B marketing leader; chronicled inbox fatigue and reply triggers |
| Amanda Natividad | VP Marketing, SparkToro | [linkedin.com/in/amandanat](https://www.linkedin.com/in/amandanat/) | Audience research expert; writes from the recipient side of pitches |
| Melissa Grabiner | Global TA Leader | [linkedin.com/in/melissa-grabiner](https://www.linkedin.com/in/melissa-grabiner/) | #1 HR creator; daily hiring-manager perspective on recruiter outreach |
| Hung Lee | Curator, Recruiting Brainfood | [linkedin.com/in/hunglee](https://www.linkedin.com/in/hunglee/) | Aggregates recruiter and HM inbox patterns across the industry |
| Gergely Orosz | Author, The Pragmatic Engineer | [linkedin.com/in/gergelyorosz](https://www.linkedin.com/in/gergelyorosz/) | Engineering leader inbox; documents recruiter outreach that fails |
| Jan Tegze | Author, Full Stack Recruiter | [linkedin.com/in/jantegze](https://www.linkedin.com/in/jantegze/) | Recruiter-turned-critic; details what hiring managers reject |
| Adam Karpiak | Recruiter & LinkedIn creator | [linkedin.com/in/akarpiak](https://www.linkedin.com/in/akarpiak/) | Posts HM reactions to outreach; bridges sender and recipient views |

## Repo Structure

```
personal-portfolio/
├── README.md                              ← you are here
└── cold-outreach-recipient-intelligence/
    ├── README.md                          # project-level overview
    ├── research/
    │   ├── sources.md                     # annotated expert list with collection status
    │   ├── linkedin-posts/               # per-expert folders with post content
    │   │   ├── peep-laja/
    │   │   ├── andrew-gazdecki/
    │   │   ├── ... (10 experts)
    │   ├── youtube-transcripts/           # video transcripts with timestamps
    │   └── other/                         # reddit threads, secondary sources
    ├── scripts/
    │   └── collect_research.py            # automated collection pipeline
    ├── synthesis/
    │   └── playbook-for-100hires.md       # final recipient-validated playbook
    └── raw/                               # raw Gemini Deep Research outputs
```

## Collection Pipeline

Built a 515-line Python script (`scripts/collect_research.py`) using:
- **YouTube Data API v3** — searches channels by keyword, pulls transcripts with timestamps
- **Reddit public JSON API** — searches subreddits for cold-outreach sentiment threads

### What worked
- Pulled 2 full YouTube transcripts from Gergely Orosz's channel (The Pragmatic Engineer)
- Both are real auto-generated transcripts with timestamps, not summaries

### What didn't work
- **Exit Five** and **Recruiting Brainfood** returned 0 YouTube results — their content lives on podcast platforms, not YouTube
- **Reddit API** returned 403 errors — Reddit has been restricting unauthenticated JSON API access
- **LinkedIn** has no public API for post content — used Gemini Deep Research to approximate post themes and positions

### Adaptation
When APIs failed, switched to Gemini Deep Research to surface expert profiles, recurring themes, and approximate LinkedIn post content. All AI-synthesized content is explicitly flagged as unverified.

## What's Complete vs. Incomplete

- [x] Expert selection and annotation (10 experts, all annotated in `sources.md`)
- [x] YouTube transcripts (Gergely Orosz — 2 videos with timestamps)
- [x] Reddit sentiment research (AI-assisted, 15 curated findings)
- [x] LinkedIn post collection (AI-synthesized — manual verification pending)
- [x] Synthesis playbook drafted
- [ ] Manual LinkedIn post verification against actual profiles
- [ ] YouTube transcripts for remaining 9 experts
- [ ] Newsletter excerpts (Recruiting Brainfood, Pragmatic Engineer)

## Synthesis

The final playbook is at [`synthesis/playbook-for-100hires.md`](cold-outreach-recipient-intelligence/synthesis/playbook-for-100hires.md) — a practical negative-constraint framework for 100hires' SDRs covering what gets deleted, what gets a reply, and one rule: respect their time more than you value your quota.