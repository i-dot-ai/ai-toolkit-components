# Turn any website into a searchable AI brain

**In about 10 minutes, you'll be able to ask Claude: "What's on my website about X?" -- and get real answers.**

Here's what you're going to do: take a website (we'll use the [i.AI Knowledge Hub](https://ai.gov.uk/knowledge-hub/)), feed all its pages into a local search engine on your laptop, and then plug it into Claude Desktop so Claude can search it during a conversation.

No coding. No cloud accounts. No API keys. Just copy-paste the commands below.

### What you'll end up with

- A **local search engine** full of website content, running on your machine
- **Claude Desktop** that can search it when you ask questions
- A **beautiful interactive map** of all the pages, colour-coded by type

By the end, you'll be able to open Claude Desktop and type:

> *"What tools on the Knowledge Hub help with public consultations?"*

...and Claude will search your local database and answer with real results, links, and relevance scores.

---

## Before you start: how to open Terminal

You'll be pasting commands into **Terminal** -- a built-in app on every Mac.

**How to open it:** Press **Cmd + Space** (Spotlight), type `Terminal`, and press Enter.

A window with a text prompt will appear. This is where you'll paste every command in this guide. Each command is in a grey box -- just copy the whole thing, paste it into Terminal, and press **Enter**.

> **Windows users:** Use **PowerShell** (search for it in the Start menu). Most commands are the same.

---

## Part A: Get your machine ready

*Skip this part if you already have Docker, Git, and uv installed.*

**You need three things installed. Each one takes about a minute.**

### A1. Install Docker Desktop

Docker is an app that runs the search engine in an isolated container -- think of it like a virtual mini-computer inside your laptop.

1. Go to https://www.docker.com/products/docker-desktop/
2. Download the version for your machine (Mac, Windows, or Linux)
3. Install it like any other app
4. **Open Docker Desktop** and wait for the whale icon in your menu bar to stop animating

> **Check it works:** In Terminal, paste: `docker --version`
> You should see something like `Docker version 27.x.x` -- the number doesn't matter, as long as it doesn't say "not found".

### A2. Install Git

Git lets you download the code from GitHub.

**Mac:** Paste this into Terminal:
```bash
xcode-select --install
```
A popup will appear -- click "Install" and wait for it to finish.

**Windows:** Download from https://git-scm.com/download/win and install it.

> **Check it works:** `git --version`

### A3. Install uv

uv is a tool that runs the bridge between Claude Desktop and your search engine. Paste this into Terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then **close Terminal and open a new one** (this is important -- it won't work in the same window).

> **Check it works:** `uv --version`

### Part A done -- you won't need to do any of that again.

---

## Part B: Build the search engine

*One-time setup. Takes about 2 minutes.*

### B1. Download the code

Paste this into Terminal:

```bash
git clone https://github.com/<your-org>/kh-blueprints.git
cd kh-blueprints
```

> This downloads the project and moves you into its folder.

### B2. Build the containers

```bash
docker compose build vector_db data_ingestor
```

This builds two things:
- **vector_db** -- the search engine (powered by Qdrant)
- **data_ingestor** -- the tool that reads websites and feeds them into the search engine

You'll see lots of text scrolling past. Wait until you see:

```
 vector_db      Built
 data_ingestor  Built
```

### Part B done -- that's the only time you need to build. From now on it's all instant.

---

## Part C: Feed in a website

*This is the fun part. Takes about 2 minutes.*

### C1. Start the search engine

```bash
docker compose --file applications/mcp_datastore/docker-compose.yaml up -d vector_db
```

Wait about 5 seconds, then check it's running:

```bash
curl http://localhost:6333/healthz
```

> `curl` is a built-in command that visits a web address from Terminal. You should see: **`healthz check passed`**

You can also see a visual dashboard by opening this link in your browser:

**http://localhost:6333/dashboard**

### C2. Choose what to ingest

We've included a ready-made list of ~80 pages from the i.AI Knowledge Hub. To use it, skip straight to step C3.

**Want to use a different website instead?** Create a text file called `my_urls.txt` with one web address per line. You can create it in any text editor (TextEdit, Notepad, VS Code) and save it inside the `kh-blueprints` folder:

```text
https://your-website.gov.uk/
https://your-website.gov.uk/about/
https://your-website.gov.uk/team/
https://your-website.gov.uk/services/service-one/
https://your-website.gov.uk/services/service-two/
```

> **Pro tip:** Many websites publish a list of all their pages at `/sitemap.xml`. Try visiting `https://your-site.com/sitemap.xml` in your browser -- you can grab URLs from there.

### C3. Run the ingestor

**Using the Knowledge Hub (the pre-built example):**

```bash
docker compose --file applications/mcp_datastore/docker-compose.yaml run --rm -v "$(pwd)/applications/mcp_datastore/knowledge_hub_urls.txt:/app/urls.txt" data_ingestor -f /app/urls.txt -c knowledge_hub
```

**Using your own website (if you created `my_urls.txt` above):**

```bash
docker compose --file applications/mcp_datastore/docker-compose.yaml run --rm -v "$(pwd)/my_urls.txt:/app/urls.txt" data_ingestor -f /app/urls.txt -c my_collection
```

> Replace `my_collection` with a short name for your project (e.g. `team_wiki`, `policy_docs`).

You'll see each page being read and processed:

```
Fetched https://ai.gov.uk/knowledge-hub/tools/consult/ (status 200, 14234 chars)
Parsed ... title='Consult', content_length=2249
...
Stored 73/73 documents in 'knowledge_hub'
Done. Ingested 73 document(s).
```

> The first run downloads a small AI model (~80 MB) to understand the text. This only happens once.

### C4. Check it worked

```bash
curl -s http://localhost:6333/collections/knowledge_hub | python3 -m json.tool | grep points_count
```

You should see `"points_count": 73` (or however many pages you ingested).

Or just refresh the dashboard in your browser: **http://localhost:6333/dashboard** -- click on the `knowledge_hub` collection to see your documents.

### Part C done -- your website is now a searchable knowledge base running locally on your laptop.

### What just happened behind the scenes?

For each URL, the system:

1. **Downloaded** the web page
2. **Extracted** the main content (ignoring menus, footers, and scripts)
3. **Converted** the text into a mathematical fingerprint (a "vector") that captures its meaning
4. **Stored** the fingerprint alongside the full text in the search engine

Pages about similar topics now have similar fingerprints. That's how it can search by *meaning* instead of just matching exact words.

---

## Part D: Plug it into Claude Desktop

*This is the big payoff. Takes about 3 minutes.*

You're going to tell Claude Desktop: "there's a search engine on my laptop -- you're allowed to use it."

### D1. Find your two paths

You need two pieces of information. Paste these into Terminal and note down the results:

```bash
which uv
```
> This prints something like `/Users/yourname/.local/bin/uv`. Copy it.

```bash
pwd
```
> This prints something like `/Users/yourname/Documents/GitHub/kh-blueprints`. Copy it.

### D2. Open the Claude Desktop config file

The easiest way: open Claude Desktop, go to **Settings** (gear icon), click **Developer**, then click **Edit Config**.

Or paste this into Terminal:

```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### D3. Add the search engine connection

The file will open in a text editor. It might be empty or have some existing content.

**If the file is empty or doesn't exist,** paste in this whole block (replacing the two paths with your values from step D1):

```json
{
  "mcpServers": {
    "knowledge-hub": {
      "command": "/YOUR/UV/PATH/HERE",
      "args": [
        "run",
        "--with", "fastmcp",
        "--with", "qdrant-client[fastembed]",
        "fastmcp", "run",
        "/YOUR/REPO/PATH/HERE/applications/mcp_datastore/mcp_server.py"
      ]
    }
  }
}
```

**For example**, if `which uv` gave you `/Users/jane/.local/bin/uv` and `pwd` gave you `/Users/jane/Documents/kh-blueprints`, it would look like:

```json
{
  "mcpServers": {
    "knowledge-hub": {
      "command": "/Users/jane/.local/bin/uv",
      "args": [
        "run",
        "--with", "fastmcp",
        "--with", "qdrant-client[fastembed]",
        "fastmcp", "run",
        "/Users/jane/Documents/kh-blueprints/applications/mcp_datastore/mcp_server.py"
      ]
    }
  }
}
```

**If the file already has content** (e.g. other MCP servers), add `"knowledge-hub": { ... }` inside the existing `"mcpServers"` block, separated by a comma.

Save and close the file.

### D4. Restart Claude Desktop

This is important -- **fully quit** Claude Desktop (**Cmd+Q** on Mac) and reopen it. Just closing the window isn't enough.

### D5. Check it connected

In the Claude Desktop message box, look for a small **hammer icon** (bottom-right area). Click it. You should see two tools listed:

- **search_knowledge_hub** -- searches your knowledge base
- **list_knowledge_hub_stats** -- shows what's in your database

> **Don't see the hammer?** Check: Is Docker still running? (whale icon in menu bar). Did you fully quit Claude Desktop (Cmd+Q) and reopen? Are the paths in the config file correct? Check for typos.

### D6. Try it!

Type any of these into Claude Desktop:

> *"Search the Knowledge Hub for AI tools that help with document translation"*

> *"What tools on the Knowledge Hub help with public consultations?"*

> *"Find me prompts for writing a business case"*

> *"What's in the knowledge hub about healthcare AI?"*

Claude will search your local database and answer with real results, including page titles, links, and how relevant each result is.

### Part D done -- Claude Desktop can now search your knowledge base.

---

## Part E: See the interactive map

One more treat. Open this in your browser:

```bash
open applications/mcp_datastore/vignettes/knowledge-hub-explorer.html
```

This is a visual map of every page you ingested. Each glowing dot is a page, positioned so that **pages about similar topics appear near each other**:

- **Blue dots** = Tools (Redbox, Consult, Minute, etc.)
- **Green dots** = Use Cases (real-world deployments)
- **Purple dots** = Prompts (business cases, risk plans, etc.)
- **Yellow dots** = How-to Guides
- **Pink dots** = Capability Pages
- **Grey dots** = Overview Pages

**Hover** over any dot to see a preview. **Click** to read the full details. **Click the legend** to show/hide categories.

Notice how the prompts cluster together on the left, the tools cluster on the right, and related pages (like "Consult" the tool and "Consult" the use case) sit right on top of each other. That's the embedding model understanding meaning.

---

## Want to use a different website?

Everything above used the Knowledge Hub as an example. Swapping in your own site takes three changes:

### 1. Create your URL list

Make a `my_urls.txt` file with your website's pages, one per line.

### 2. Run the ingestor with a new collection name

```bash
docker compose --file applications/mcp_datastore/docker-compose.yaml run --rm -v "$(pwd)/my_urls.txt:/app/urls.txt" data_ingestor -f /app/urls.txt -c my_project_name
```

### 3. Tell the MCP server which collection to search

Add a `"COLLECTION_NAME"` setting to your Claude Desktop config:

```json
"knowledge-hub": {
  "command": "/your/uv/path",
  "args": ["run", "--with", "fastmcp", "--with", "qdrant-client[fastembed]", "fastmcp", "run", "/your/repo/path/applications/mcp_datastore/mcp_server.py"],
  "env": {
    "COLLECTION_NAME": "my_project_name"
  }
}
```

Then restart Claude Desktop (Cmd+Q and reopen).

### Quick reference

| I want to... | Do this |
|-------------|---------|
| Use a different website | Create a new `my_urls.txt` with your URLs |
| Name my collection | Use `-c your_name` when running the ingestor |
| Add more pages later | Run the ingestor again with the new URLs (existing pages won't be duplicated) |
| Speed up ingestion | Edit `applications/mcp_datastore/code/data_ingestor/config/config.yaml` and change `request_delay` to `0.5` |
| Search a different collection from Claude | Add `"env": {"COLLECTION_NAME": "your_name"}` to the config |
| Run multiple websites | Ingest each into a different collection name, add multiple entries to the Claude Desktop config |

---

## Stopping and starting again

```bash
# Stop the search engine (keeps your data)
docker compose --file applications/mcp_datastore/docker-compose.yaml stop

# Start it again later
docker compose --file applications/mcp_datastore/docker-compose.yaml up -d vector_db
```

> **Important:** Use `stop` (not `down`) if you want to keep your data. `down` removes the container and everything in it.

---

## How it works (optional reading)

You don't need to understand this to use it, but if you're curious:

**The core idea:** Every piece of text can be converted into a list of 384 numbers (a "vector") that represents its meaning. Texts about similar topics produce similar numbers. To search, you convert your question into the same kind of numbers and find the closest matches.

```
1. FETCH       Download each web page
2. PARSE       Extract the main content (strip menus, footers, scripts)
3. EMBED       Convert text into a 384-number fingerprint using an AI model
4. STORE       Save the fingerprint + full text in the search engine
5. SEARCH      Convert your question into a fingerprint, find the closest matches
6. MCP         The bridge that lets Claude Desktop trigger step 5
```

| Component | Plain English | Technology |
|-----------|--------------|------------|
| vector_db | The search engine | Qdrant |
| data_ingestor | Reads websites and feeds them in | Python + BeautifulSoup + FastEmbed |
| mcp_server.py | The bridge to Claude Desktop | FastMCP |
| Embedding model | Converts text to number fingerprints | all-MiniLM-L6-v2 (80 MB, runs locally) |

---

## Something not working?

| What's happening | What to do |
|-----------------|------------|
| `command not found: docker` | Docker Desktop isn't installed, or isn't running. Open it and wait for the whale icon to settle. |
| `connection refused` when checking health | The search engine isn't running yet. Run the `docker compose ... up -d vector_db` command and wait 10 seconds. |
| The ingestor says `403 Forbidden` | That website blocks automated visitors. Not all websites allow this. |
| Some URLs show `404` | Those pages don't exist. Just remove them from your URL list and run the ingestor again. |
| Claude Desktop doesn't show the hammer icon | Check: (1) Docker is running, (2) you fully quit Claude with Cmd+Q and reopened, (3) the paths in the config file are correct and absolute (start with `/`). Check logs at `~/Library/Logs/Claude/mcp*.log`. |
| First run is slow | The AI model downloads once (~80 MB). After that, everything is cached. |
| `command not found: uv` | Close Terminal and open a **new** one. uv needs a fresh Terminal after installation. |
