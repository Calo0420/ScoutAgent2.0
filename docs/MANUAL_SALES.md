# ScoutAgent 2.0 — Sales Playbook

**Everforth (an Apex Systems company) | Infrastructure Practice**
**For Everforth Sales Team Use Only — Not for Client Distribution**

---

## Table of Contents

1. [Your 30-Second Pitch](#1-your-30-second-pitch)
2. [Before the Meeting](#2-before-the-meeting)
3. [Running the Demo](#3-running-the-demo)
4. [Walking the Client Through the Report](#4-walking-the-client-through-the-report)
5. [Handling Objections](#5-handling-objections)
6. [Closing](#6-closing)
7. [Quick Reference Card](#7-quick-reference-card)

---

## 1. Your 30-Second Pitch

Memorize this. Practice it until it is completely natural. Use it verbatim.

---

> *"Most clients know they have technical debt and security gaps — they just don't know where or how much it's costing them. ScoutAgent connects to your infrastructure — Linux, Windows, VMware, all of it — reads everything in a single pass, and produces a board-ready report in under ten minutes. It finds the specific servers with security holes, calculates the exact cost of your VMware licensing waste, and gives you a 90-day roadmap to fix it — all without touching a single configuration. We use it to walk every new client through exactly what they have before we propose anything. Want to see it run on a demo environment right now?"*

---

**Why this works:**
- Opens with the client's pain ("know they have technical debt")
- States a specific, remarkable outcome ("board-ready report in under ten minutes")
- Anchors to money ("exact cost") and risk ("specific servers with security holes")
- Ends with a direct invitation to see it in action

---

## 2. Before the Meeting

### 48 Hours Before

- [ ] Confirm who is in the room. Know before you walk in: who is the CIO, who is the CFO, who is the CISO or security lead. Each person needs to hear a different thing from the report (covered in Section 4).
- [ ] Review the client's industry. Healthcare and finance clients will ask about data privacy first — have the Bedrock/air-gap story ready. See Section 5.
- [ ] Print or save a copy of the sample report (SAMPLE_REPORT.md or the PDF version). Bring it as a leave-behind.

### Day of Meeting

- [ ] Open your laptop. Have the ScoutAgent UI already loaded in a browser tab: `http://<host>:7070`.
- [ ] Run the demo scenario once before the meeting to confirm it still works — pick a preset (Typical Client or High Risk are good defaults for most audiences) and click RUN SCAN.
- [ ] Demo mode needs no target credentials and makes no real connections — safe to run cold, won't fail on missing access.
- [ ] Have the report modal ready to reopen, or the browser tab positioned so you can pull it back up immediately.
- [ ] Close all other applications. Full screen is more compelling. No notifications.
- [ ] Have this question ready to ask early: *"Before I show you the demo — what does your current infrastructure assessment process look like today?"* Their answer will tell you exactly which parts of the report to emphasize.

### What to Bring

- [ ] Laptop with ScoutAgent running (demo mode verified)
- [ ] Printed sample report (1 copy per attendee is ideal)
- [ ] One-page capability overview (ask your manager for the current version)
- [ ] Business cards

---

## 3. Running the Demo

### Setting the Stage

Before you type anything, say this:

> *"What I'm going to do is run ScoutAgent against a demo environment we use for exactly this purpose — it has a typical mid-size company's infrastructure profile: a few Linux servers, a VMware cluster, and a network segment. The vulnerabilities and cost issues are realistic. It'll take about 60 seconds to run, and then I'll walk you through what it found."*

This framing does three things: it explains the demo, it sets a realistic time expectation, and it tells them the findings are realistic (not toy examples).

### Running the Demo

Click the accelerator toggles relevant to the story you want to tell, pick a scenario preset (or leave individual toggles as-is for a custom mix), and click **RUN SCAN**.

Say as you click:

> *"This is the only thing I need to do — pick what we're assessing, and click one button. ScoutAgent handles everything from here."*

### While It Runs (What to Say)

As the agent runs, narrate what is happening at a high level. Do not explain technical details. Use language like:

- *"It's connecting to the servers now and reading the configuration..."*
- *"Now it's checking the security benchmarks — there's a set of CIS controls it tests against..."*
- *"This part is the VMware scan — it's reading the virtual machine inventory from vCenter..."*
- *"And now the AI is synthesizing all of it into the report..."*

### What NOT to Say

- Do not say "Claude" or "Anthropic" unless asked. Say "the AI" or "the AI engine." Some clients have vendor preferences or procurement sensitivities.
- Do not say "it might not find anything" or hedge the demo outcome. The demo environment is configured to have findings.
- Do not apologize for the terminal. If someone looks confused by the command line, say: *"This is what your IT team runs — what I'm showing you is the output they hand to leadership."*
- Do not try to explain paramiko, pyVmomi, or nmap unless someone explicitly asks how the scans work technically.

### When It Finishes

The demo completes in approximately 60–90 seconds in demo mode. When you see the report generate, say:

> *"There it is. Sixty seconds. Let me show you what's in here."*

Then move to Section 4.

---

## 4. Walking the Client Through the Report

Different people in the room need to hear different things. Here is exactly what to emphasize for each audience.

---

### If You Have a CIO in the Room

**Focus on:** The Executive Summary (Section 1) and the Migration Roadmap (Section 6).

**What to say:**

> *"This first section is written specifically for a CIO — no technical jargon. It tells you the overall risk rating, the top three things that need action, and what each one will cost to fix. Everything else in this report is evidence supporting these three priorities. You shouldn't need to read past page two unless you want the detail."*

Then point to the top priority recommendation and say:

> *"This is the first thing we'd tackle. Here's why it matters from a business perspective — [read the business impact, not the technical detail]. The effort estimate is right here. This is a fixed-scope engagement, not open-ended."*

**Language to use with a CIO:** Risk exposure, business continuity, timeline, effort estimate, fixed scope.

**Language to avoid:** Kernel versions, SSH configuration, CVE numbers.

---

### If You Have a CFO in the Room

**Focus on:** The Savings Estimate (Section 4) and License Cost Comparison (Section 5).

**What to say:**

> *"This section is the financial case. The agent found [X] virtual machines that are powered off but still consuming VMware licenses. That's [dollar amount] per year in pure waste — nothing needs to be migrated, just decommissioned. That's the conservative number. This column here shows the moderate scenario, which includes rightsizing the oversized VMs. And the aggressive column includes migration-eligible Windows servers moving to Linux."*

Then point to the confidence level:

> *"We're transparent about confidence. High confidence means we had complete data. Medium means we estimated some numbers — you'll see the assumptions noted. We don't give you a number we can't stand behind."*

**Language to use with a CFO:** Annual savings, break-even, confidence level, 3-year projection, recoverable budget.

**Language to avoid:** VMware licenses (say "virtualization licensing"), vCPU count, technical migration complexity.

---

### If You Have a CISO in the Room

**Focus on:** The Risk Map (Section 3).

**What to say:**

> *"The risk register lists every security finding with a likelihood score, an impact score, and a combined rating. These are not theoretical vulnerabilities — each one is tied to a specific host. Critical findings are scored 20 to 25, high is 12 to 19. We highlight two things immediately: any Critical finding needs a scheduled remediation window this week, and we flag any finding combinations that are more dangerous together than apart."*

Then point to any critical finding and say:

> *"This one, for example — root SSH is enabled on this host. That alone is a high finding. But paired with auditd being disabled on the same host, you have an active attack vector with no logging. That means if someone exploits it today, you won't know until damage is done. That's why it's flagged as a combination risk."*

**Language to use with a CISO:** Risk rating, attack vector, exploit, remediation window, audit trail, CIS benchmark compliance, logging baseline.

**Language to avoid:** "This is easy to fix" (let them ask). Do not downplay Critical findings.

---

### If You Have an IT Manager or Technical Lead

**Focus on:** Server Inventory (Section 2) and Migration Roadmap (Section 6).

**What to say:**

> *"The inventory table is a complete asset register — every server we touched, fully documented. The flags in red are your immediate action items. Each flag type is defined consistently: PATCH GAP means it hasn't been patched in more than 60 days, STABILITY RISK means it hasn't been rebooted in more than 90 days. If AI/ML workloads are in scope, there's also an AI stack readiness read — GPU presence, model-serving tooling, vector databases — worth showing if this client has any AI initiatives underway, since most haven't had that inventoried at all."*

For the roadmap:

> *"Phase 1 is security hardening — 30 days, specific servers listed, hour estimates included. Phase 2 is stabilization. Phase 3 is where migration begins. The out-of-scope table at the end is as important as the roadmap itself — it shows what we're not touching and why."*

**Language to use with an IT manager:** Specific server names, specific hour estimates, phase prerequisites, success criteria.

---

## 5. Handling Objections

### "Is our data safe?"

**What they mean:** They're asking whether their infrastructure data — hostnames, IP addresses, vulnerabilities — is being sent somewhere they can't control.

**Answer:**

> *"That's exactly the right question to ask. ScoutAgent gives you four deployment options precisely because of this concern. The default mode sends findings to the Anthropic API over encrypted HTTPS — similar to how you'd use any secure cloud service. But if you have data residency requirements or a compliance program that doesn't allow data leaving your environment, we run it in AWS Bedrock mode, where everything stays within your own AWS account. Nothing leaves your cloud. And if you're in an air-gapped environment with no internet access at all, we have an on-premises mode using a local AI model. The assessment runs completely inside your four walls. We also offer a fourth option through Venice AI if you prefer open-source models without an Anthropic account. You pick the mode that fits your security policy."*
>
> **The governance layer most assessment tools don’t have:** every action the agent takes passes through Gatekeeper, our AI trust gateway. You authorize the session before it reads anything. It is allowed to see configuration and posture — but the moment it reaches for an actual secret — a `.env` file or a private key — Gatekeeper blocks the read and logs the attempt. You get a signed audit trail of every access, allowed or blocked, sealed with a SHA-256 hash you can verify yourself. “Is our data safe” stops being a promise and becomes something you can prove.

---

### "How is this different from what we already have?"

**What they mean:** They're thinking of tools like Nessus, Qualys, Tenable, or whatever vulnerability scanner their team already uses.

**Answer:**

> *"Great question — and the short answer is that ScoutAgent is not a vulnerability scanner. Traditional tools give you a list of CVEs. ScoutAgent gives you a board-ready business document. It connects the technical findings to dollar amounts, risk ratings, and a specific 90-day action plan written for leadership, not for the IT team. The IT team already has the scanner output — what the CIO and CFO need is something they can act on without a 10-hour technical translation exercise. That's what ScoutAgent produces, and it does it in minutes, not weeks."*

If they press for more technical comparison:

> *"Think of it this way: a scanner finds the vulnerability. ScoutAgent answers the question 'so what does this mean for the business, and what are we going to do about it?' Different tools, different audiences."*

---

### "What does implementation look like?"

**What they mean:** They're asking about commitment — time, disruption, and what they need to provide.

**Answer:**

> *"There's almost nothing on your side to prepare. You need to give us a read-only SSH account on the Linux servers you want assessed — no sudo, no admin access, just read access. If you have VMware, a read-only vCenter account. That's it. We handle the rest. The assessment itself takes under 10 minutes and makes no changes to any of your systems. After the assessment, we present the report within 24 hours and walk your team through the findings. The first engagement is the assessment. Whether we do the remediation work or you handle it internally, you'll have a clear, prioritized plan either way."*

---

### "Can it run in our environment?"

**What they mean:** They may have network restrictions, air-gap requirements, or specific OS versions they're worried about.

**Answer:**

> *"Yes, in most cases. ScoutAgent needs TCP 22 for standard SSH to reach your Linux servers, WinRM (5985) for your Windows servers, and HTTPS to reach vCenter if you have VMware — it covers a mixed environment in one pass, not just one OS. If you're running in an air-gapped environment with no outbound internet, we use the on-premises Ollama mode — no external connectivity required at all. If you have strict data residency requirements, we use your own AWS account through Bedrock. If you prefer open-source models without an Anthropic account, we can run through Venice AI. The tool is designed to meet you where your security policy already is, not to require exceptions to it."*

If they ask about specific Linux distributions:

> *"It works on any Linux distribution with standard SSH — RHEL, CentOS, Rocky, Ubuntu, Debian. The underlying commands it runs are standard POSIX utilities."*

---

### "This sounds like it could find things we don't want exposed — what happens to those findings?"

**What they mean:** They're concerned about liability or about findings being shared beyond their organization.

**Answer:**

> *"Findings go only where you tell them to go. The report is a local file — it never gets transmitted to Everforth's servers or anywhere else automatically. In Bedrock or Ollama mode, it doesn't even leave your environment. Our engagement model treats assessment output as client confidential. We don't aggregate findings across clients. If you want to run the assessment and have only your internal team see the output, that's completely your call."*
>
> **And the agent never reads the contents in the first place:** Gatekeeper detects that a credential file or private key exists — worth knowing — but blocks the agent the instant it tries to open one, and logs every attempt. In a recent live assessment it caught the agent reaching for ten credential files and stopped all ten. The things you do not want exposed are never read, and you hold a tamper-evident record proving it.

---

## 6. Closing

### What to Leave Behind

Every meeting should end with the client holding three things:

1. **A printed copy of the sample report.** Let them hold it. The physical weight of a 10-page detailed technical report produced in 60 seconds is part of the story.
2. **Your business card.** With your direct line, not just your email.
3. **A clear next step** — see below.

### What to Ask For Next

Do not leave without naming a specific next step. Pick one of these based on the conversation:

**If they're interested but cautious:**
> *"Here's what I'd suggest: let us run a real assessment on a single non-production server in your environment. No VMware, no full network scan — just one Linux host. 10 minutes. You see a real report from your real infrastructure. No commitment to anything after that."*

**If they're engaged and the budget conversation went well:**
> *"The way we typically move forward is a scoping call with your IT lead — 30 minutes — to identify the right servers and confirm the credentials access. We schedule the assessment, run it, and have the report reviewed with your team within a week. Do you want to set that up before we leave today?"*

**If the CISO or security team lead was in the room and engaged:**
> *"If it would be useful, we can put together a 1-page summary of the risk findings from the demo alongside your environment profile — something you could share with your security team as context for the conversation. Would that be helpful?"*

### Things to Never Do

- Do not promise a specific savings number without running a real assessment. The demo numbers are from a synthetic environment.
- Do not commit to a project timeline or price on the spot. The assessment scopes the work — that's literally its purpose.
- Do not leave without a named next step and a date. "I'll follow up" is not a next step.

---

## 7. Quick Reference Card

*Print this page separately and keep it in your bag.*

---

### The One-Line Hook

*"ScoutAgent finds your security gaps and VMware waste in under 10 minutes — and produces a board-ready report your CIO can act on without calling a meeting."*

---

### The Demo Action

Pick a scenario preset, click **RUN SCAN**.

Say while it runs: *"It's scanning the environment... reading the security configuration... checking VMware... now the AI is writing the report..."*

---

### Three Things Each Persona Cares About

| CIO | CFO | CISO |
|---|---|---|
| Risk rating + top 3 priorities | Annual savings number | Risk register — Critical findings |
| 90-day roadmap | Confidence level | Finding combinations |
| Effort estimates | 3-year projection | Remediation windows |

---

### The Four Objections + One-Line Responses

| Objection | Your One-Liner |
|---|---|
| "Is our data safe?" | "Four modes: cloud API, your AWS, fully on-prem, or open-source via Venice. You pick based on your policy." |
| "We already have a scanner" | "Scanners find CVEs. ScoutAgent produces a board-ready business document in 10 minutes." |
| "What does implementation look like?" | "Read-only SSH account, 10 minutes, no changes to any system." |
| "Can it run in our environment?" | "Yes — including air-gapped. We meet your security policy, not the other way around." |

---

### Next Steps (Pick One)

- **Cautious:** Single server pilot, no commitment
- **Engaged:** 30-min scoping call, assessment within a week
- **Security-focused:** 1-page risk summary for their security team

---

### Leave Behind Checklist

- [ ] Printed sample report
- [ ] Business card (direct line on it)
- [ ] Named next step with a date

---

*Everforth Infrastructure Practice | An Apex Systems Company*
*ScoutAgent 2.0 Sales Playbook | For Internal Use Only*
