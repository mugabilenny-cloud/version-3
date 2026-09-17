# Switch — local-data build with auth, hierarchy search, and embedded video

This is the six-original-screen "Switch" UX prototype (Home / My Courses /
Course Detail / Upload / Saved / Viewer), wired to the course-content
spreadsheet instead of a live Supabase project, with local file-backed auth
added on top. No external database, no network calls at runtime except the
YouTube and Google Docs/Drive iframe embeds themselves — everything else
reads from JSON files bundled in the repo.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

First run: you'll land on the sign-up/login screen (`pages/0_Auth.py`).
Sign up, pick your current semester from the real list the data has, and
you're in for up to 3 days without needing to log in again.

## What's here

**Local data layer (no external database).** `supabase_client.py`'s live
HTTP/RPC calls are replaced by `tree_store.py` (loads `data/tree.json`,
provides tree/search/grouping) and `local_client.py` (same function names
and shapes `supabase_client.py` had, so every page's import line was the
only required change versus the original prototype).

**Local auth (no external database, no plaintext passwords).** `local_auth.py`
— PBKDF2-HMAC-SHA256 with a random per-user salt; the raw password is never
written to disk. Session tokens (not passwords) persist across reloads via
`st.query_params`, file-backed in `data/sessions.json` with a 3-day expiry.
A valid session skips straight to Home with no re-prompt; an expired or
missing one routes to `pages/0_Auth.py`.

**Hierarchy-aware search.** `TreeStore.search()` tags node hits with which
tree level matched (faculty/department/course_unit/etc.) and link hits with
whether the query matched a title or a url, instead of one flat undifferentiated
list. `local_client.search_courses()` surfaces both to the search box.

**Per-topic grouping in Course Detail.** Every row in `repo_5.xlsx` ends its
path in the literal segment `"Class"`, so a course unit's 14+ links (for
Pathophysiology, for example) all share one tree node — see the caveat
below. `TreeStore.links_for_node_grouped()` splits them back into their real
topics (Epilepsy 2, Meningitis, Stroke, etc.) using each link's own `title`
field, and Course Detail renders a labeled section per topic instead of one
flat pile of cards.

**Red-coded inline YouTube embeds.** `tree_store.youtube_video_id()` extracts
the video id from a youtube url; `ui_components.youtube_embed()` renders an
actual playable iframe; `video_resource_card()` wraps that in a styled card
with a red (`#DC2626`) type chip. Reachable from Course Detail, Saved, Home's
search results, and the Viewer page.

**Embedded Google Docs/Drive viewing.** `tree_store.drive_embed_url()`
recognizes a docs.google.com or drive.google.com url (Docs, Sheets, Slides,
or a generic Drive file link) and builds Google's own iframe-embeddable
`/preview` (`/embed` for Slides) address; `ui_components.drive_doc_embed()`
renders it, the note/doc (`drive_notes`/`drive_questions`) equivalent of the
YouTube embed above. The Viewer always shows a direct "Open in Google Docs"
link alongside the embed — a document that isn't shared "Anyone with the
link" will show Google's own access-denied page inside the iframe rather
than failing visibly, so the direct link is there regardless of whether the
embed itself looks like it worked. A url that doesn't match a recognized
Google Docs/Drive shape falls back to a plain link instead of an embed
attempt; a resource with no url at all gets a plain "link unavailable"
message instead of either.

**Per-user history and saved items.** `local_history.py` and `local_saved.py`
— file-backed, so a save or a "recently opened" entry survives a closed tab
within your 3-day session, not just the current browser tab.

## The data

`data/tree.json` was generated from `repo_5.xlsx` by `tools/import_content.py`.
Re-run it if the spreadsheet changes:

```bash
python tools/import_content.py path/to/repo_5.xlsx
```

Current import: **24 nodes, 157 links** (30 of them YouTube videos with
real, working urls).

### Two things worth knowing about the source data — not bugs, don't "fix" these

1. Every path in `repo_5.xlsx` ends in the literal segment `"Class"` rather
   than a per-topic name — this is why the title-based grouping above exists
   at all. The fix is at the link-grouping level (already built), not by
   trying to split `"Class"` into separate tree nodes.
2. The source file has two slightly different department-name spellings
   under Health Sciences (`"BMS   0000"` with extra internal spaces, and
   plain `"BMS"`) that produce two separate tree nodes rather than merging.
   This may reflect a real distinction in the source data — don't silently
   merge these.

### A note on dead/inaccessible drive_notes / drive_questions links

Unlike the YouTube urls above, the `drive_notes`/`drive_questions` urls in
the source spreadsheet have not been individually verified as reachable —
some have been reported dead or inaccessible. That's a property of the
spreadsheet data (and, for a url that does resolve, of that Google Doc's
own sharing setting — it needs to be shared "Anyone with the link" for
Google's `/preview` embed to render for someone who isn't signed into the
owner's account), not something `tools/import_content.py` or the Viewer can
repair on their own. Two things do help track it down:

- The importer now warns (to stderr, at the end of the import) about any
  url that doesn't start with `http://`/`https://` — a cheap, mechanical
  check that catches an obviously-broken cell, not a dead-but-well-formed
  one.
- A resource that has no url at all, or a url that isn't a recognized
  Google Docs/Drive address, gets a distinct "unavailable" or "can't
  preview inline" message in the Viewer instead of either a blank iframe or
  the fully-generic placeholder — see "Embedded Google Docs/Drive viewing"
  above.

Actually confirming which specific rows are dead means opening each url and
checking its sharing setting directly.

## What's intentionally NOT here

- **Ads / "What's New on Campus" feed** — no ads table exists locally, so
  `fetch_feed()` returns empty and that section stays hidden.
- **Student uploads / crowdsourcing** — the Upload screen is still a
  placeholder form; content is added by re-running the importer.
- **PDF/slide inline preview** — still shows a placeholder box in the
  Viewer rather than a real renderer. In practice this only matters if the
  data grows a `pdf`/`ppt` file type later: the current importer only ever
  produces `video`/`note`/`doc` from the source spreadsheet's `youtube` /
  `drive_notes` / `drive_questions` link kinds, and video and note/doc both
  get a real embed now (see "Embedded Google Docs/Drive viewing" above).
- **A password-change or account-settings screen** — sign-out exists (top
  right of Home); nothing else account-related does yet.

## Project layout

```
app.py                  entry point — auth gate, routes to Home or sign-in
local_auth.py           local hash+salt auth, 3-day sessions (data/users.json,
                         data/sessions.json)
local_history.py        per-user "recently opened" (data/history.json)
local_saved.py          per-user saved/bookmarked items (data/saved.json)
ui_components.py        shared widgets — cards, tiles, nav, youtube embeds
local_client.py         drop-in for supabase_client.py — same functions,
                         backed by tree_store.py instead of HTTP
tree_store.py           loads data/tree.json, tree-walk + search + grouping
pages/
  0_Auth.py             sign-up / login
  1_Home.py             search, active-semester tiles, recent history, feed
  2_My_Courses.py
  3_Course_Detail.py    topic-grouped resources, video embeds
  4_Upload.py
  5_Saved.py
  6_Viewer.py           full-resource view, video/doc embeds, history recording
tools/
  import_content.py     xlsx -> data/tree.json converter
data/
  tree.json             generated — do not hand-edit; re-run the importer
  users.json, sessions.json, history.json, saved.json
                         generated at runtime as people sign up and use the
                         app — not checked in with real data
assets/manifest.json
.streamlit/config.toml
```
