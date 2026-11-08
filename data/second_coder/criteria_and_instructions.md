# Second-coder tasks — *Efficient Tool Use for Agentic AI* (survey)

Thank you for doing this. There are two independent tasks. Your answers are compared with the first author's
to report inter-rater agreement (Cohen's κ) in the paper. Please work **independently**:

- Don't look at the survey's bibliography, its benchmark table (Table 4 / Section X), or its data repository
  while coding.
- Don't discuss individual records with Hossein until both tasks are finished.
- If you hesitate, still give an answer and mark it *unsure*. Don't leave items blank.

**Easiest way:** use the web sheet Hossein shares with you (one tab per task; it saves as you go and shows your
progress). The CSV files in this folder are the same items for offline work; return the two filled templates if
you use them instead.

| Task | Items | Time | Input file | Return |
|---|---|---|---|---|
| 1. Abstract screening | 100 arXiv records | ~2–3 h | `screening_records.csv` | `screening_answers.csv` |
| 2. Benchmark audit | 43 benchmark papers | ~4–6 h | `benchmarks_to_audit.csv` | `audit_answers.csv` |

---

## Task 1 — Abstract screening

Decide from the **title and abstract** whether each record belongs in the survey. Open arXiv only when the
abstract is ambiguous.

**Include** when the work is about large language models or LLM agents calling tools (tools, function calling,
APIs, MCP, code execution used as a tool), **and** it does at least one of the following:

1. proposes or studies a method that changes the cost of tool use: which tools enter the prompt, how many calls
   or turns an episode takes, how calls are executed, how much tool output stays in context, or which model
   makes the calls;
2. builds or uses a benchmark to evaluate tool use;
3. surveys tool use or agent efficiency.

**Exclude** everything else, for example software "tools" unrelated to LLMs, LLM work where tools are incidental,
or applications that use function calling without studying its cost or evaluating it.

### Output format: `screening_answers.csv`

Start from `screening_answers_TEMPLATE.csv` (one row per record, already numbered). Keep `n` and `arxiv_id`
unchanged.

| Column | Required | Allowed values |
|---|---|---|
| `n` | given | 1–100 |
| `arxiv_id` | given | e.g. `2501.01234` |
| `decision` | **yes** | `include` or `exclude` |
| `reason` | recommended | if include: `selection`, `planning`, `invocation`, `context`, `models`, `benchmark`, `survey`, `other`<br>if exclude: `not_llm_tools`, `incidental`, `no_cost_eval`, `other` |
| `unsure` | yes | `1` if unsure, else `0` |
| `note` | no | free text (quote it if it contains commas) |

Reason codes:

| Code | Meaning |
|---|---|
| `selection` | Tool selection & retrieval: choosing which tools or schemas are shown to the model |
| `planning` | Planning & call reduction: fewer calls or turns; plan-then-execute; batching |
| `invocation` | Invocation & execution: parallel or asynchronous calls, caching, serving, code execution |
| `context` | Context & tool results: compressing or filtering tool outputs and history |
| `models` | Models & training: small or fine-tuned tool-calling models; training data for tool use |
| `benchmark` | Benchmarks, datasets, or evaluation studies of tool use |
| `survey` | Reviews of tool use or agent efficiency |
| `other` (include) | Fits the criteria but none of the above |
| `not_llm_tools` | Not about LLM tool use |
| `incidental` | Tools are incidental, or an application only |
| `no_cost_eval` | About tool use, but no cost or evaluation angle |
| `other` (exclude) | Any other reason (say which in `note`) |

Example rows:

```csv
n,arxiv_id,decision,reason,unsure,note
7,0000.00001,exclude,incidental,1,"chatbot for a hospital; uses function calling but studies neither cost nor evaluation"
8,0000.00002,include,selection,0,
```

---

## Task 2 — Benchmark audit

For each of the 43 benchmark papers, read the **latest arXiv version, body and appendices** (`pdf_url` in
`benchmarks_to_audit.csv`), and decide for each of four metrics whether the paper **reports it as a result for
the agents or models it evaluates**.

| Column | Metric | Counts when the paper reports, for evaluated agents… |
|---|---|---|
| `money` | `$` monetary cost | dollars (or another currency) per task, per run, or in total |
| `latency` | `L` latency / time | wall-clock time or latency |
| `tokens` | `Tk` tokens | input, output, or total token counts |
| `calls` | `C` calls / turns / steps | number of tool calls, turns, rounds, or steps per task |

**Does not count:** dataset statistics (e.g. turns per dialogue in the data, tools per task); the cost of
building or annotating the dataset; context length or catalog size used as a difficulty variable; budgets or
limits the harness imposes, unless the paper also reports what agents actually used; numbers that appear only in
task text, examples, or the references.

**Procedure.** Search the PDF for `$`, USD, dollar, cost, price, latency, wall-clock, time, second, token, call,
turn, step, round, and read every match in context. For each metric you mark `yes`, write where it is and the
number in `evidence`. Expect 5–10 minutes per paper.

### Output format: `audit_answers.csv`

Start from `audit_answers_TEMPLATE.csv`. Keep `n`, `bibkey`, `benchmark`, and `arxiv_id` unchanged.

| Column | Required | Allowed values |
|---|---|---|
| `money`, `latency`, `tokens`, `calls` | **yes, all four** | `yes` or `no` |
| `other` | no | any other efficiency metric the paper reports for agents (free text) |
| `evidence` | **yes for every `yes`** | location and number, e.g. `C: Table 4, 9.3 tool calls per task` |
| `unsure` | yes | `1` if unsure about any of the four, else `0` |
| `note` | no | free text |

Example row:

```csv
n,bibkey,benchmark,arxiv_id,money,latency,tokens,calls,other,evidence,unsure,note
99,example2026bench,ExampleBench,0000.00003,yes,no,yes,yes,,"$: Table 3, $0.12 per task; Tk: Table 3, 41k input tokens per task; C: Sec. 5.1, 9.3 calls per task",0,
```

(The examples are invented and show the format only; they are not in your lists.)

---

## Returning your answers

- **Web sheet:** click *Mark … as finished* on each tab. If the sheet says it is saving in your browser only,
  click *Copy all answers* on each tab and email the text to Hossein.
- **Offline:** email `screening_answers.csv` and `audit_answers.csv` (UTF-8, comma-separated, with the header row).
