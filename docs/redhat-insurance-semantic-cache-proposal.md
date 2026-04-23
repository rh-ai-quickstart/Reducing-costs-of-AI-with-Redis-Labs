# Proposal: Joint Redis + Red Hat quickstart for insurance claims AI

## Proposal summary

We propose building a joint Redis + Red Hat quickstart that demonstrates how **Redis semantic caching on OpenShift AI** can reduce LLM cost and improve response time for an **insurance claims assistant**.

The core story is practical and easy to explain:

- insurance claims assistants receive many repeated questions with different wording
- Redis can answer many of those questions from a semantic cache instead of calling the LLM every time
- OpenShift AI provides the platform for deploying the app, notebooks, and evaluation workflow

This gives us a clear joint value proposition: **better AI economics and better user experience on OpenShift**.

## What we are proposing to build

We propose building a **repo and demo** with the following components:

1. **Insurance claims assistant application**
   - a lightweight API service deployed on OpenShift
   - optional simple chat UI for demo purposes
   - request handling that checks Redis semantic cache before calling the LLM

2. **Redis semantic cache layer**
   - use Redis as the semantic cache for repeated or paraphrased claim questions
   - recommended v1 path: **LangCache / Redis Cloud** because it aligns with the reference notebook and keeps the first release lightweight
   - future option: in-cluster Redis deployment for a later phase if desired

3. **Insurance knowledge pack**
   - a small set of insurance claims FAQ and policy guidance documents
   - examples covering auto and homeowner claims topics such as deductibles, required documents, rental reimbursement, glass claims, and next steps after filing

4. **Cache warming / Doc-to-Cache notebook**
   - a notebook that turns source content into FAQs
   - preloads Redis with high-confidence answers
   - allows threshold tuning and cache evaluation

5. **Evaluation harness**
   - a synthetic workload of common, paraphrased, and negative test questions
   - a baseline mode with no cache
   - a cache-enabled mode with Redis semantic cache
   - output showing hit rate, latency, and estimated LLM cost savings

6. **OpenShift deployment assets**
   - Helm chart updates for app configuration, secrets, routes, and validation
   - documentation and architecture diagrams suitable for a Red Hat AI quickstart

## The specific v1 demo we should build

To keep this focused, I recommend a very specific v1:

### Demo title

**Reduce insurance claims assistant cost with Redis semantic cache on OpenShift AI**

### Demo behavior

The demo will answer common questions such as:

- What documents do I need to file an auto claim?
- Do I need photos for a windshield claim?
- When does rental reimbursement apply?
- When do I pay my deductible?
- What happens after I submit a claim?

The app will:

1. receive a user question
2. classify whether it is safe to attempt a semantic cache match
3. check Redis for a semantically similar cached answer
4. return the cached answer on a hit
5. call the LLM / RAG path on a miss
6. record latency and cache statistics for reporting

## What is intentionally out of scope for v1

To keep the story credible and achievable, v1 should **not** try to solve live claims operations.

Out of scope:

- claim-status lookups
- payout or estimate updates
- adjuster assignment questions
- policy administration workflows
- integration with real insurer backend systems

These are not good semantic-cache candidates because the answer can change even when the question is semantically similar.

## Why insurance claims is the right use case

Insurance claims support has the right traffic pattern for semantic caching:

- high repetition of user intent
- lots of paraphrasing
- many stable answers grounded in policy/process content
- easy to simulate with a synthetic workload
- easy to explain to customers and partners

This makes it much easier to show a clean before/after story than a broad generic assistant demo.

## Why this is a strong Red Hat partnership story

This proposal gives each party a clear role:

- **Red Hat / OpenShift AI**: platform for deploying the assistant, notebooks, jobs, routes, and optional model endpoint
- **Redis**: semantic cache that reduces repeated LLM calls and improves response time

The combined message is straightforward:

> Run enterprise AI apps on OpenShift AI and use Redis to control cost and improve responsiveness.

## Recommended architecture for the quickstart

- **OpenShift / OpenShift AI**
  - assistant API
  - optional demo UI
  - evaluation notebook or job
  - secrets and route management
- **Redis**
  - semantic cache for common claims FAQ questions
- **LLM endpoint**
  - bring-your-own LLM endpoint or OpenShift-hosted endpoint
- **Knowledge assets**
  - insurance FAQ and policy guidance content

## What the repo should contain

The repo should ship with concrete assets, not just notebooks:

- `app/` - API service for the assistant
- `chart/` - Helm chart for OpenShift deployment
- `docs/` - proposal, architecture, and usage docs
- `notebooks/` or demo notebook content - Doc-to-Cache and threshold tuning
- `data/` - synthetic insurance FAQ and evaluation datasets
- `scripts/` or job templates - evaluation runner and cache warmup logic

## Success criteria for the demo

The quickstart should show a measurable before/after result that Red Hat can reuse in field conversations.

Suggested success metrics:

- cache hit rate on the synthetic workload
- number of avoided LLM calls
- estimated token cost reduction
- median and p95 latency improvement
- acceptable precision at the chosen similarity threshold

Example framing:

- baseline: 100 insurance questions, 100 LLM calls
- cache-enabled: 100 insurance questions, materially fewer LLM calls depending on threshold and cache quality

## Recommended implementation approach

For v1, I recommend this exact build plan:

1. start with **managed Redis semantic cache** to reduce deployment complexity
2. deploy the assistant service and demo assets on **OpenShift AI**
3. preload the cache from curated insurance FAQ content
4. run a synthetic workload to generate a before/after comparison
5. package the result as a reusable Red Hat AI quickstart

This keeps the first release focused on the value story, not on infrastructure plumbing.

## Current gap between the proposal and the repo

The current `Reducing-costs-of-AI-with-Redis-Labs` area is still a starter skeleton. To match this proposal, it still needs:

- assistant application deployment
- Redis config and secret handling
- cache warmup job or notebook-driven preload flow
- evaluation runner
- service and route templates
- finished README and architecture assets

## Recommendation to share with Red Hat

The most specific proposal to share is:

> We propose building a joint OpenShift AI quickstart for an insurance claims assistant that uses Redis semantic cache to answer common, non-temporal claims questions more efficiently. The quickstart will include an OpenShift-deployed app, a Redis-backed semantic cache, a small insurance knowledge pack, a notebook for cache warming and threshold tuning, and an evaluation workflow that shows before/after LLM cost and latency improvements.

## Next step

If Red Hat agrees with this direction, the immediate next step should be to align on:

- the exact v1 use case: insurance claims FAQ assistant
- the exact deployment model: OpenShift-hosted app + managed Redis semantic cache
- the exact demo output: before/after savings and latency story

That gives us a specific, achievable joint build with a clear business message.