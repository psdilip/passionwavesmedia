---
title: I Tried to Replace Claude Code With a Local LLM. Here's Everything I Learned.
slug: replacing-claude-code-with-local-llm
category: AWS
tags: AI, LLM, Local LLM, Claude Code, Ollama, LM Studio, Hardware, AWS
excerpt: A journey through RAM upgrades, hallucinated tool calls, context windows, and the honest limits of consumer hardware — and where I landed instead.
date: 2026-07-29
---

![Photo by Petr Urbanek on Unsplash](https://images.unsplash.com/photo-1762508346277-7938c42e2eef?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Petr Urbanek](https://unsplash.com/@r4o4) on [Unsplash](https://unsplash.com)*

## The starting point

It began with something simple: upgrading the RAM on my MSI Aegis ZS gaming desktop (Ryzen 5 5600X, RX 6700 XT, 12GB VRAM) from 16GB to 48GB. The goal was bigger than gaming — I wanted to run local LLMs for coding, for privacy-sensitive work, and to see how close I could get to the experience of a paid Claude Code subscription, but free and fully private.

Part of what pushed me there was just noticing how token usage actually works with a hosted subscription. Tokens are like credits in a game — the more you burn through, the sooner you're out of runway for the session. That got me curious about open-source models I could run myself: things released by Google, Mistral AI, and Alibaba's Qwen team, downloadable and free to use without a meter running.

What followed was a multi-week debugging odyssey across LM Studio, Ollama, Continue.dev, Cline, Aider, and OpenCode. Here's what actually happened, and what I wish someone had told me on day one.

## Lesson 1: RAM is not the bottleneck you think it is

I assumed more RAM would directly translate to faster, smarter local models. It doesn't — not the way GPU VRAM does.

- **VRAM is the racetrack.** It's fast (the RX 6700 XT runs about 384GB/s of memory bandwidth) and it's where inference actually happens.
- **RAM is the parking lot.** It's where model layers spill over when they don't fit in VRAM — and that spillover is slow, because data has to shuttle back and forth over the PCIe bus.

My RX 6700 XT has 12GB of VRAM. That number — not my 48GB of system RAM — was the real ceiling the entire time. A model that fits entirely in VRAM runs fast. A model that overflows into RAM runs at a fraction of the speed, no matter how much RAM you throw at it.

**Takeaway:** for local LLMs, check your GPU's VRAM first. RAM upgrades help you fit bigger models; they don't make them fast.

![Photo by Daniel Hatcher on Unsplash](https://images.unsplash.com/photo-1520520688967-7bdc16e77dc2?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Daniel Hatcher](https://unsplash.com/@handsel) on [Unsplash](https://unsplash.com)*

## Lesson 2: picking RAM sticks taught me about timings, not just speed

![Photo by Andrey Matveev on Unsplash](https://images.unsplash.com/photo-1760708626495-91e1415be067?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Andrey Matveev](https://unsplash.com/@zelebb) on [Unsplash](https://unsplash.com)*

Before even touching AI tooling, I had to pick RAM. A few things mattered more than I expected:

- **CL (CAS latency) matters as much as MHz.** A DDR4-3600 CL16 kit can outperform a DDR4-3600 CL18 kit at the same frequency, because CL16 responds faster per cycle. Real-world latency in nanoseconds — roughly `(CL ÷ (MT/s ÷ 2)) × 1000` — is a better comparison than either number alone.
- **AMD Ryzen 5000-series CPUs have a sweet spot around DDR4-3600MHz.** The Infinity Fabric syncs 1:1 with RAM up to about that speed; pushing higher can decouple the fabric and hurt performance instead of helping it.
- **Mixing kits (different capacity, speed, or timings) drops everything to the lowest common denominator.** When I added 2x16GB sticks to my existing 2x8GB sticks, I couldn't just enable XMP — the board wouldn't apply a profile built for one kit across mismatched modules. The fix was manually setting a frequency both kits could handle (2666MHz) and disabling XMP entirely.

**Takeaway:** buying RAM isn't just "get the biggest number." Match kits when you can, and understand that BIOS auto-detect defaults to the safest, slowest option unless you configure it yourself.

## Lesson 3: the real villain was the context window, not the models

This was the single biggest revelation of the entire journey, and it took the longest to surface.

Every tool I tried — Claude Code pointed at Ollama, Continue.dev, Cline, OpenCode — eventually produced the same failure signature: instead of actually reading files or running commands, the model would output a fake, hallucinated tool call, something like:

```
{"name": "read_file", "arguments": {"filepath": "main.tf"}}
```

My instinct each time was to blame the model. Too small. Wrong architecture. Not "smart enough" for tool calling. So I cycled through model after model — 32B, 27B, 14B, 1.5B, Gemma — convinced the next one would finally be capable enough.

It never was, because the actual problem was invisible: Ollama's default context window is small (often just 4,096 tokens unless you override it). Coding agents like Claude Code, Cline, and OpenCode send a system prompt plus a full list of tool definitions before your question even arrives — often 10,000 to 30,000 tokens on its own. With a 4K window, that payload gets silently truncated. The model never sees the tools it's supposed to call, so it pattern-matches on fragments and hallucinates what a tool call should look like.

This explained months of confusing, contradictory behavior:

- Different models failing identically → not a model problem, a truncation problem.
- LM Studio throwing a loud error (`n_keep >= n_ctx`) while Ollama failed silently — LM Studio was actually the more honest failure.
- OpenCode "giving up" after a few prompts — the context filled up over the course of the conversation, the middle got silently discarded, and the model lost track of the task.

The fix: build a custom Modelfile that explicitly raises the context window:

```
FROM qwen2.5-coder:14b
PARAMETER num_ctx 32768
PARAMETER temperature 0.1
```

Setting context length in a tool's own config file (like `opencode.json`) isn't enough — it only tells the editor when to compact conversation history. The actual model context has to be set via a Modelfile, or with the `OLLAMA_CONTEXT_LENGTH` environment variable.

**Takeaway:** if a local model seems to "give up," hallucinate tool calls, or behave inconsistently across totally different model sizes, check the context window before you touch the model at all.

![Photo by Bernd Dittrich on Unsplash](https://images.unsplash.com/photo-1774901128283-64c62117216a?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Bernd Dittrich](https://unsplash.com/@hdbernd) on [Unsplash](https://unsplash.com)*

## Lesson 4: fixing context exposes the second bottleneck

Raising the context window didn't fully solve things — and here's the trap I fell into repeatedly: fixing layer one (context) exposes layer two (VRAM).

A 14B model with a proper 32K context window needs roughly:

- ~9.5GB for model weights (at typical quantization)
- +4-6GB for KV cache at that context length
- ≈ 14-15GB total

My GPU has 12GB of VRAM. So the same fix that stopped the hallucinations introduced overflow into system RAM — which, per Lesson 1, is dramatically slower. The model would now try to execute tools correctly, but take 45-90 seconds to do it, tripping timeouts in tools like Cline (30-second default).

This two-layer bottleneck is why the whole thing felt like whack-a-mole: small context → fast but hallucinating; large context → honest but crawling. Both symptoms look like "the model gave up," but they have opposite causes.

**Takeaway:** local LLM performance is a balance between context window size and VRAM capacity — you can't maximize both on a 12GB card without trade-offs.

## Lesson 5: model family matters more than model size

Not all models are trained the same way for tool calling. I learned this the hard way after cycling through Qwen2.5-Coder at multiple sizes with identical failures.

- **Dense models** (like `qwen2.5-coder:14b`) activate all their parameters for every token — slower, and not necessarily trained with reliable function-calling patterns.
- **MoE (Mixture of Experts) models** like Qwen's `qwen3:30b-a3b` have a large total parameter count (30B) but only activate a small fraction (roughly 3B) per token — delivering closer to "big model" reasoning at "small model" speed.
- **Purpose-built agentic models**, like Mistral's Devstral, are trained specifically for tool-calling reliability, which matters more for agent workflows than raw parameter count.

I also learned to distrust model names before checking their actual specs — on my setup, `ollama show` reported that a couple of the largest tags I pulled required far more memory than my hardware had, likely cloud-routed variants rather than something meant to run locally at all. Always check the real spec before assuming a tag matches your hardware.

**Takeaway:** when picking a local coding model, prioritize models explicitly trained for tool/function calling over simply picking a bigger parameter count.

## Lesson 6: different local tools, different rule files, same underlying problem

Once I moved from raw Ollama into actual coding agents (Continue.dev, Cline, Aider, OpenCode), I found every tool has its own convention for "project rules":

| Tool | Rule file |
|---|---|
| Cline / Roo Code | `.clinerules/` directory |
| Claude Code, OpenCode, Aider, Copilot, Cursor, and 30+ others | `AGENTS.md` (an emerging shared standard) |
| Aider (alternate) | `.aider.conf.yml` |

Rather than duplicating rules per tool, the better structure was a root-level configuration that cascades into individual projects:

```
repos/                     ← global rules (immutable security baseline)
├── AGENTS.md
├── .clinerules/
│   ├── 01-identity.md
│   ├── 02-code-standards.md
│   ├── 03-security.md
│   └── 04-behavior.md
├── opencode.json
│
├── project-a/
│   └── AGENTS.md          ← extends root, can't override security rules
└── project-b/
    └── AGENTS.md
```

The mental model that made this click: it's like federal law versus state law. The root file sets non-negotiable baselines (no hardcoded secrets, least-privilege IAM, mandatory QA gates). Project-level files can add stricter rules or project-specific context, but can never weaken the security floor.

**Takeaway:** don't rebuild your rules per project. Build once at the root, extend per project, and lean toward `AGENTS.md` as the baseline since the most tools support it natively.

![Photo by David Kristianto on Unsplash](https://images.unsplash.com/photo-1754379656510-928c56cb5c87?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [David Kristianto](https://unsplash.com/@davidkristianto) on [Unsplash](https://unsplash.com)*

## Lesson 7: even the "right" setup has a hardware ceiling

After fixing context windows, matching model families to the task, structuring rule files, and tuning permissions, local agents did start executing real tool calls. But the honest comparison against cloud Claude Code stayed lopsided:

| | Claude Code (cloud) | Local Qwen/Devstral (RX 6700 XT) |
|---|---|---|
| Response time | 3-8 seconds | 15-90 seconds |
| Context window | ~200K tokens | ~32K tokens (practical ceiling) |
| Tool-calling reliability | Consistent | Model-dependent, still occasionally unreliable |
| Cost | Subscription | $0 after hardware + time investment |
| Privacy | Code leaves the machine | 100% local |

The uncomfortable truth: a 12GB consumer gaming GPU isn't built for agentic LLM workloads at the speed cloud infrastructure delivers. Multi-file autonomous coding loops — the kind Claude Code does without much drama — want 24GB+ of VRAM to run at a comparable pace, which is RTX 3090/4090 territory.

**Takeaway:** know what your hardware is actually for. A 12GB card is legitimately good for private chat-style assistance, documentation, and single-file edits. It's not yet a drop-in replacement for a cloud agent doing rapid multi-file refactors.

## Where I landed: back to Claude Code, with a local layer underneath

I went through a real tour before settling anywhere: Ollama first, because it's the simplest way to get a model running. Then LM Studio, which was genuinely useful for a different reason — it exposes parameters clearly, lets you host on your local network so other machines can hit the same model, and makes the VRAM-vs-RAM split visible instead of hidden. I also tried OpenCode against free-tier models, and NVIDIA's own API catalog for a wider model selection — both useful, both capped by usage limits soon enough.

None of it matched Claude Code on the thing that actually matters for agentic coding: context window, response speed, and how consistently it gets the task done the way I meant it. So that's what I came back to for real coding-agent work, and I built a local layer around it instead of trying to replace it outright.

**CLAUDE.md** is the first file Claude reads for a project — project-specific instructions, conventions, gotchas. Mine merges this repo's own context with a set of behavioral guidelines inspired by ideas Andrej Karpathy has written about publicly on how LLMs tend to fail in coding contexts: don't touch code you weren't asked to touch, don't assume — ask, clean up only the mess your own change made, and verify your own work before calling it done. (You can see that exact section in this repo's own `CLAUDE.md`, since I wrote it in while working on this site.)

**graphify** is the other half. It turns a whole repo into a knowledge graph — communities of related files, functions, and concepts, closer to an Obsidian-style mind map than a flat file tree. Instead of Claude re-reading every file from scratch each session, it can query the graph directly, which meaningfully cuts token usage on a large or long-running project.

Day to day, I stopped defaulting to the most expensive/highest-effort model for everything — Sonnet 4.6 at medium effort covers the large majority of what I actually need, and I explicitly instruct it to ask about anything ambiguous and double-check its own work rather than push forward on a guess. It's not perfect, but the instruction to surface uncertainty instead of hiding it catches most of what would otherwise become a wasted round-trip.

One thing I'm holding onto loosely: one of Claude Code's own creators has talked about periodically deleting your skills and CLAUDE.md files — every six months or so — and running without them for a while, just to see how much the underlying model has actually improved on its own. His point was that scaffolding you built around a weaker model's limitations can quietly become dead weight once the model itself gets better at the things you were compensating for. I haven't done that test yet, but it's a good discipline: the goal isn't to accumulate rules forever, it's to only keep the ones still doing real work.

The next piece I haven't wired in yet: an AWS MCP server. Since a good chunk of what I use Claude for is AWS architecture review and API work, pulling live documentation straight from the source instead of relying on training data would close a real gap.

## A closing thought on the trade-off

![Photo by Kevin Ache on Unsplash](https://images.unsplash.com/photo-1695668548342-c0c1ad479aee?w=1600&q=80&fm=jpg&fit=crop)
*Photo by [Kevin Ache](https://unsplash.com/@kevinache) on [Unsplash](https://unsplash.com)*

None of the local-LLM detour was wasted effort. What felt like weeks of chasing my own tail — swapping models, fighting timeouts, second-guessing hardware — actually mapped out the whole stack: context windows, VRAM/RAM trade-offs, tool-calling reliability, rule-file architecture. That's a real, transferable skill set, and it now runs quietly in the background of my workflow instead of being the main event.

The local setup isn't trying to beat Claude Code anymore. It does the job it's actually good at — private, free, always-available — while the heavy lifting still goes to the cloud. That division of labor, once I stopped fighting it, is what made the whole system feel finished instead of perpetually "almost working."

One honest caveat, and this is opinion, not a claim about any specific company's numbers: running everything through a closed-source cloud model means that work is ultimately backed by real data centers, real GPUs, real electricity and water for cooling. I don't have hard figures on any one provider's footprint, and I'm not claiming to. But it's part of why I find the trajectory of more efficient open-source models worth rooting for — every bit of capability that can run on a laptop or a single consumer GPU instead of a data center is less infrastructure someone has to spin up on your behalf. That's a preference, not a verdict.

What I keep coming back to is simpler than any of the hardware math: the gap between an idea and a working version of it has genuinely shrunk. The only thing actually standing between a problem worth solving and a working solution is doing the work.

## Practical guide: if you want to try this yourself

A condensed version of everything above, in the order I'd actually do it if starting over:

1. **Check your GPU's VRAM before buying anything.** VRAM decides which models are viable at usable speed; system RAM only decides how badly a model that doesn't fit will overflow.
2. **Set `OLLAMA_CONTEXT_LENGTH` (or a custom Modelfile with `PARAMETER num_ctx`) before connecting any coding agent.** This one step would have eliminated most of the "hallucinated tool call" debugging described above.
3. **Pick a model built for tool calling** — an agentic-trained model (like Devstral) or an MoE model (like Qwen3's `-a3b` variants) — instead of defaulting to the largest dense model that technically fits in VRAM.
4. **Verify a model's real memory requirements with `ollama show <model>`** before assuming the name or parameter count in the tag matches what will actually run on your hardware.
5. **Build your agent rules once, at the root of wherever your repos live**, using `AGENTS.md` (or `.clinerules/` if your tool requires it) — then let individual projects extend it instead of rebuilding it per repo.
6. **Match the model to the task, not the other way around:** local for privacy-sensitive, offline, or single-file work; cloud for multi-file refactors, anything time-sensitive, or anything where tool-calling reliability actually matters.
7. **Set expectations early.** A 12GB consumer GPU is a genuinely useful complement to a cloud coding agent — not a replacement, at least not until VRAM crosses somewhere around the 24GB line.
