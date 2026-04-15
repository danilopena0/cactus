# Dark Code: Agent Security and the Limits of Explainability

A few months ago, a founder I know had a data leak that took his security team four days to understand. That's a long time for a CEO to be glued to an incident channel.

Customer data from one tenant was showing up in another tenant's dashboard. Earlier, a non-technical but high-agency employee had connected a customer data API into a reporting pipeline. An agent in the middle selected steps at runtime, and one of those steps cached results somewhere another service could read.

Every individual service stayed within its permissions. Nothing was obviously misconfigured. If you reviewed each component in isolation, you wouldn't have seen the issue. The path only existed at runtime, assembled by an agent that no longer existed by the time anyone went looking.

When the security lead tried to answer the most basic question—who did this—they couldn't. There was a workflow someone had set up, an agent executing it, a chain of tools. You could reconstruct what happened from the logs. You couldn't cleanly assign it to a single actor.

I've seen versions of this pattern across companies in our portfolio and beyond. The details vary; the structure doesn't. It's showing up in the largest organizations too: at Meta, an internal agent bypassed a human review step while still passing identity checks. Salesforce's Agentforce had a vulnerability in which instructions embedded in a web form could cause the agent to exfiltrate CRM data through a trusted domain.

Cross-tenant exposure, supply-chain failures, agent leaks, credentials ending up where they shouldn't: these are no longer edge cases. They're the background condition. I've been calling it "dark code."

## What Is Dark Code

Dark code is behavior in production that nobody can explain end-to-end. Not just unreviewed code, but systems whose behavior emerges from interactions between components—often at runtime—without anyone ever holding a complete mental model of what the system actually does.

For a long time, writing code more or less forced a degree of understanding—not because engineers were unusually careful, but because the process was slow enough that authorship and comprehension stayed coupled. We've always had exceptions: copied snippets, opaque dependencies, config files nobody touched after Jeff left. But those systems were usually stable. They failed in recognizable ways, and you could trace them after the fact. That relationship is breaking.

## What's Different Now

What's different now isn't just speed or volume. It's the kind of system being produced.

Part of the change is structural: agents select tools at runtime, execution paths don't exist until they run, and natural language increasingly acts as a control plane. The thing determining behavior is no longer just code or API calls, but a prompt interpreted in context. When one agent calls another, there often isn't a strict schema—just a model interpreting language. Some of the most consequential behavior in these systems may never appear in source code at all.

The rest is simpler: code is being produced faster than understanding can catch up. Tests pass, diffs look clean, everything ships—but there may never have been a moment when anyone understood the system as a whole.

This isn't limited to application code. Build pipelines, release processes, secrets management—users are clamoring to automate them the same way, with the same gap. The systems that determine who-can-access-what are themselves becoming harder to fully review. Dark code in an application is a liability. Dark code in the security layer is worse.

## The Expanding Builder Population

The builder population has expanded enormously. People outside engineering can now create production-adjacent behavior: someone in marketing connects tools for outbound, a PM wires something directly to production data because the interface makes it easy. Often the result is useful. The shift is that system-creating power is now widely distributed, while accountability and review are not.

We've seen a version of this before—SaaS sprawl, shadow IT. The difference now is that people aren't just connecting existing services. They're creating new behavior, and that behavior can come into existence when someone describes it in English.

## Why Existing Controls Fall Short

Our existing controls were not built for this. We have distributed tracing, zero trust, runtime observability—but those tools were designed for systems whose complexity was at least deliberate. Here, generating novel behavior is part of normal operation. Charles Perrow had a term for failures like these: "normal accidents." Not caused by error or negligence, but built into the structure of any system too complex for its operators to hold in their heads. The SOC 2 report looks the same whether your system has three agent-driven workflows or three hundred, and that's not good enough.

Shipping before you fully understand what you've built isn't a character flaw. Today, it's how you compete. But there's a gap between "we move fast" and "we cannot tell you what our system did with your data last week." Customers didn't choose to be on this side of it.

## The Questions That Will Come

The questions are arriving faster than the infrastructure to answer them. Procurement still asks about SOC 2 and encryption at rest—controls designed for a world in which you could enumerate what software does. Almost nobody is yet asking the questions that matter now: what are your agents doing in production? Can you reconstruct a decision path? Can you say what your system actually did on a Tuesday in March?

They will.

When a cross-tenant exposure makes the wrong headline, or an agent-driven workflow leaks sensitive data in a way that can't be cleanly attributed, the question won't be whether the company had good intentions. It will be whether it maintained the ability to explain what its system actually did.

Nobody is slowing down. The real question is whether you can answer a customer who asks what your system did with their data on a specific Tuesday in March—and whether you built the infrastructure to know, or just assumed you'd figure it out when it mattered.
