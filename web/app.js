(() => {
  const $ = (id) => document.getElementById(id);
  let busy = false,
    currentPlan = null,
    lastQuestion = "";
  function node(tag, text, cls) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function notify(text, error = false) {
    $("notice").textContent = text;
    $("notice").className = error ? "error" : "";
  }
  function working(value) {
    busy = value;
    document.querySelectorAll("button").forEach((b) => {
      b.disabled = value || b.dataset.sourceUnavailable === "true";
    });
    $("make-plan").disabled = value || !lastQuestion;
  }
  async function request(path, body, method = "POST") {
    const response = await fetch(
      path,
      body === undefined
        ? { method: "GET" }
        : {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
    );
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Check the fields and try again.",
      );
    return data;
  }
  async function refresh() {
    const [docs, stats, plans] = await Promise.all([
      request("/api/documents"),
      request("/api/stats"),
      request("/api/plans"),
    ]);
    $("document-count").textContent = stats.documents;
    $("plan-count").textContent = stats.plans;
    $("review-count").textContent = stats.review_events;
    $("documents").replaceChildren();
    for (const d of docs) {
      const row = node("article", undefined, "document");
      const remove = node("button", "Remove", "text");
      remove.setAttribute("aria-label", "Remove note " + d.title);
      remove.onclick = async () => {
        if (busy) return;
        working(true);
        try {
          await request("/api/documents/" + d.id, {}, "DELETE");
          lastQuestion = "";
          $("evidence").replaceChildren(
            node(
              "p",
              "Source shelf changed. Run the question again to refresh the evidence.",
            ),
          );
          if (currentPlan)
            renderPlan(await request("/api/plans/" + currentPlan.id));
          await refresh();
          notify("Note and its saved quotations removed.");
        } catch (e) {
          notify(e.message, true);
        } finally {
          working(false);
        }
      };
      row.append(
        node("b", d.title),
        node("small", `${d.characters} characters · ${d.digest.slice(0, 8)}`),
        remove,
      );
      $("documents").append(row);
    }
    if (!docs.length)
      $("documents").append(
        node(
          "p",
          "Your shelf is empty. Add notes or load the labeled examples.",
          "muted",
        ),
      );
    const selected = currentPlan?.id || "";
    $("history").replaceChildren(
      node(
        "option",
        plans.length ? "Select a saved session" : "No saved plans",
      ),
    );
    $("history").firstChild.value = "";
    for (const p of plans) {
      const opt = node("option", p.question.slice(0, 65));
      opt.value = p.id;
      $("history").append(opt);
    }
    $("history").value = selected;
  }
  const demos = [
    {
      title: "DEMO • Searching and complexity",
      text: "Synthetic demonstration note, written for this app.\n\nBinary search works on a sorted collection. Compare the target with the middle element and discard the half that cannot contain it. The interval halves after each comparison, giving logarithmic comparison complexity O(log n). An unsorted collection cannot use this procedure without first establishing order.\n\nA linear search inspects elements one by one until the target is found or all elements have been examined. Its worst-case comparison complexity is O(n).",
    },
    {
      title: "DEMO • Database transactions",
      text: "Synthetic demonstration note, written for this app.\n\nA database transaction groups operations into a unit of work. Atomicity means all its operations commit together or are rolled back together. Isolation controls how concurrent transactions observe one another.\n\nIndexes help locate rows without scanning every row, but they require storage and maintenance on writes. A query plan explains which access path the database chooses. An index is not automatically useful for every query.",
    },
  ];
  $("document-form").onsubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    working(true);
    try {
      const result = await request("/api/documents", {
        title: $("document-title").value,
        text: $("document-text").value,
      });
      $("document-form").reset();
      lastQuestion = "";
      await refresh();
      notify(
        result.duplicate
          ? "Identical text was already on your shelf."
          : "Note saved locally.",
      );
    } catch (error) {
      notify(error.message, true);
    } finally {
      working(false);
    }
  };
  $("load-demo").onclick = async () => {
    if (busy) return;
    working(true);
    try {
      for (const doc of demos) await request("/api/documents", doc);
      lastQuestion = "";
      $("question").value = "How does binary search reduce the search space?";
      await refresh();
      notify(
        "Two synthetic demo notes loaded. They are not your course materials.",
      );
    } catch (e) {
      notify(e.message, true);
    } finally {
      working(false);
    }
  };
  function renderTrace(trace) {
    $("trace").replaceChildren(node("b", "Actual workflow"));
    for (const step of trace)
      $("trace").append(node("span", `${step.tool} · ${step.result_count}`));
  }
  $("question-form").onsubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    working(true);
    lastQuestion = "";
    try {
      const q = $("question").value;
      const result = await request("/api/ask", { question: q });
      $("evidence").replaceChildren();
      renderTrace(result.trace);
      for (const [i, c] of result.citations.entries()) {
        const card = node("article", undefined, "citation");
        const top = node("div", undefined, "citation-head");
        top.append(
          node("span", `[${i + 1}] ${c.title}`),
          node("span", `${Math.round(c.relevance * 100)} / 100 text relevance`),
        );
        const details = node("details");
        details.append(
          node(
            "summary",
            `Source offsets ${c.start}–${c.end} · inspect checksum`,
          ),
          node("code", c.digest),
        );
        card.append(top, node("blockquote", c.quote), details);
        $("evidence").append(card);
      }
      if (!result.citations.length)
        $("evidence").append(
          node(
            "p",
            result.status === "no_sources"
              ? "No source notes available. Add notes first."
              : "Insufficient matching evidence. No answer was invented.",
            "empty-message",
          ),
        );
      else lastQuestion = q;
      notify(result.notice);
    } catch (error) {
      notify(error.message, true);
    } finally {
      working(false);
    }
  };
  $("question").oninput = () => {
    if ($("question").value !== lastQuestion) {
      lastQuestion = "";
      $("make-plan").disabled = true;
    }
  };
  function renderPlan(plan) {
    currentPlan = plan;
    $("plan").replaceChildren();
    const bar = node("div", undefined, "plan-bar");
    const link = node("a", "Export local plan ↗", "text");
    link.href = "/api/plans/" + plan.id + "/export";
    bar.append(
      node(
        "b",
        `${plan.total_minutes} minutes · ${plan.tasks.length} sourced tasks`,
      ),
      link,
    );
    $("plan").append(bar);
    const tasks = node("div", undefined, "tasks");
    for (const task of plan.tasks) {
      const card = node("article", undefined, "task");
      card.append(
        node(
          "span",
          `${task.minutes} MIN · ${task.state.toUpperCase()}`,
          "task-meta",
        ),
        node("h3", task.title),
        node(
          "blockquote",
          task.source_available
            ? task.citation.quote
            : "Source removed. This historical task cannot be reviewed.",
        ),
      );
      if (task.next_review_at)
        card.append(
          node(
            "p",
            "Next suggested review: " +
              new Date(task.next_review_at).toLocaleString(),
            "small",
          ),
        );
      const actions = node("div", undefined, "task-actions");
      for (const [rating, label] of [
        ["needs_practice", "Needs practice"],
        ["recalled", "Recalled it"],
      ]) {
        const b = node(
          "button",
          label,
          task.rating === rating ? "secondary chosen" : "secondary",
        );
        b.disabled = !task.source_available;
        b.dataset.sourceUnavailable = String(!task.source_available);
        b.onclick = async () => {
          if (busy) return;
          working(true);
          try {
            renderPlan(
              await request(`/api/plans/${plan.id}/tasks/${task.id}/review`, {
                rating,
              }),
            );
            await refresh();
            notify(
              "Review saved locally. Interval is a planning choice, not a mastery prediction.",
            );
          } catch (e) {
            notify(e.message, true);
          } finally {
            working(false);
          }
        };
        actions.append(b);
      }
      card.append(actions);
      tasks.append(card);
    }
    $("plan").append(tasks);
    $("history").value = plan.id;
  }
  $("make-plan").onclick = async () => {
    if (busy || !lastQuestion) return;
    working(true);
    try {
      const plan = await request("/api/plans", {
        question: lastQuestion,
        minutes: Number($("minutes").value),
      });
      renderPlan(plan);
      await refresh();
      notify("A sourced study session was saved.");
      $("plan").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      notify(e.message, true);
    } finally {
      working(false);
    }
  };
  $("history").onchange = async () => {
    if (!$("history").value) return;
    try {
      renderPlan(await request("/api/plans/" + $("history").value));
    } catch (e) {
      notify(e.message, true);
    }
  };
  refresh().catch((e) => notify(e.message, true));
})();
