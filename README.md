# ResHub

> An AI-powered platform that supports the entire research lifecycle — from idea, to literature review, to writing, to finding the right journal to publish in.

**Graduation Project** — Faculty of Information Technology, The Arab American University
Supervised by **Dr. Mohammed Maree**

---

## The Problem

Doing research is not one task — it's a dozen fragmented ones.

A researcher has to discover relevant literature, read and summarize dozens of papers, identify gaps and weaknesses in prior work, manage citations, write in correct academic English, find collaborators working on similar problems, and finally figure out *which* journal will actually accept their paper. Each of these steps lives in a different tool.

Mendeley manages references but has no AI. Google Scholar searches but doesn't collaborate. Overleaf writes but doesn't discover. ResearchGate connects but doesn't analyze. So researchers end up juggling five or six platforms, copying data between them, and losing time on coordination instead of discovery.

**ResHub brings the whole cycle into one place**, with AI doing the heavy lifting at each stage.

---

## Research & Market Study

We did not start by writing code. Before a single line was written, we ran a full research and market study phase:

- **Competitive analysis of 6 existing platforms** — Mendeley, ResearchGate, Semantic Scholar, Overleaf, Iris.ai, and Google Scholar. For each one we studied its target audience, feature set, how it actually works in practice, and where it falls short.
- **A feature-by-feature comparison matrix** mapping equivalent capabilities across all six systems against our proposed feature set, so we could see exactly which gaps were real and unaddressed.
- **Requirements engineering** derived directly from that analysis — the gaps we found in existing systems became our functional requirements, not guesses.
- **Full system modeling before implementation** — use case diagrams and detailed use case descriptions for all four user roles, sequence diagrams for every major flow, class diagrams per module, an ERD, and a complete database mapping.
- **A literature-backed foundation**, drawing on published work in semantic analysis of research abstracts, content-based recommendation for researchers, semantic web modeling, academic social network mining, and citation mapping.

The result: every feature in ResHub exists because we identified a specific, documented gap in what researchers currently have available to them.

---

## Features

### AI Literature Review Chatbot
Ask a research question in natural language. The system runs semantic search across a research-paper vector store, retrieves the most relevant sources, and generates a synthesized answer grounded in them — returning the answer **with inline citations** (title, authors, year, relevance score, and a supporting snippet from each source). Supports year filtering to scope results to a time window.

### Literature Critique & Gap Analysis
Beyond summarizing, the AI critiques the retrieved literature — surfacing strengths, weaknesses, and unaddressed gaps, so the researcher knows what their own contribution needs to be in order to be novel.

### Semantic Graph
Every researcher's interests, papers, and concepts are modeled as a graph. The system runs graph analysis over it to produce:
- Conceptually related papers via graph traversal
- Key concepts ranked by node centrality
- Research clusters via community detection
- **Potential collaborators** matched on research-interest overlap
- Emerging topics detected from temporal patterns

The graph is also rendered visually, with a focus node and adjustable traversal depth.

### Generic Journal Finder
Analyzes a paper's actual content to build a subject profile, then scores it against a journal database. Returns ranked recommendations with a fit score, impact factor, acceptance rate, average review time, open-access status, **compliance issues flagged against that journal's requirements**, and human-readable reasons for the match. It also generates a **submission plan**: required formatting changes, a submission checklist, estimated review time, and alternative journals as a fallback.

### Collaborative Workspaces
Create a shared workspace, invite members, and co-author documents inside the platform with permission-gated access.

### Academic Writing Tools
An in-platform editor with formatting support, version control, AI-assisted drafting, professional grammar checking, and citation management with ready-to-use citation files.

### Community & Profiles
Researcher profiles backed by the semantic graph, researcher search, discussion forums, document statistics (reads, downloads, comments, citations), and multi-channel notifications (in-app + email) for mentions and collaboration requests.

### Role-Based Access
Four distinct roles with tiered capabilities:

| Role | Access |
|---|---|
| **Guest** | Read published papers, watch the tutorial, register |
| **Registered User** | Full research toolkit — profile, writing tools, chatbot, critique, forums, publishing |
| **Premium User** | Everything above, plus researcher matching via semantic graph, collaborative features with matched researchers, and the journal finder |
| **Admin** | User management, content moderation, feature-access control, site theming, announcements, system logs |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask (Blueprint-based modular architecture) |
| **Auth & Sessions** | Flask-Login, role-based access control |
| **Forms & Validation** | Flask-WTF |
| **ORM & Database** | SQLAlchemy |
| **AI / LLM** | OpenAI GPT-4 for answer generation, critique, and writing assistance |
| **Retrieval** | Vector store with semantic search (RAG pipeline: retrieve → build prompt → generate → cite) |
| **Graph Analysis** | Centrality measures, community detection, graph traversal for the semantic graph |
| **Frontend** | Jinja2 templates, HTML, CSS, JavaScript |
| **Modeling & Design** | PlantUML, Draw.io |

### Architecture

Flask route handlers receive requests and orchestrate the logic layer — authentication, AI interaction, and data retrieval — then render through Jinja templates. The model layer covers database operations, research data, and chatbot logic. External services (AI APIs, encryption) are isolated in dedicated utility classes so the system stays modular and new AI-driven features can be added without touching the core.

Each major feature is a self-contained module:

```
app/
├── semantic_graph/     # SemanticGraphService — graph analysis & visualization
├── journal_finder/     # JournalFinderService — matching & submission planning
├── workspaces/         # Collaborative workspaces & documents
├── chatbot/            # RAG-based literature chatbot
└── ...
```

---

## Non-Functional Design Goals

- **Performance** — chatbot responses within a bounded time window; optimized queries and indexing
- **Scalability** — designed for high concurrent load without degradation, and for adding features without architectural rework
- **Security & Compliance** — encryption in transit and at rest, strong authentication (incl. MFA), priority-based access control, GDPR and PCI-DSS alignment, regular backups
- **Availability** — 99% minimum uptime target
- **Accessibility** — consistent navigation, accessible data visualization, and reduced data loads for users on limited internet connections
- **Usability** — usable by researchers regardless of technical background

---

## Team

Built by a team of three:

- **Khaled Saayda** — Computer Science
- **Layan Khalil** — Computer Science
- **Sally Daibes** — Computer Science

---

## Future Work

- Fine-tuning LLMs on domain-specific research corpora for deeper, more personalized results
- Integrating more advanced NLP models
- Expanded collaborative workspace features
- Multi-language interface support
- Direct integrations with international institutions and publishers for a fully connected research ecosystem

---

## License

<!-- Add your license here, e.g. MIT -->
