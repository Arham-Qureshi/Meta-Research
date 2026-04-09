# Contributing to Meta-Research 🚀

First off, thank you for considering contributing to Meta-Research! It's people like you that make open-source such an amazing place to learn, inspire, and build. 

Whether you're here to fix a bug, optimize an algorithm, or add a shiny new feature to the citation graph visualizer, we welcome your contributions. 

## What is Meta-Research?

Meta-Research isn't just another CRUD app. We act as a powerful layer on top of academic knowledge, heavily leaning into:
- **API Aggregations:** Connecting arXiv, Crossref, OpenAlex, and Semantic Scholar.
- **LLM Integrations:** Making papers conversational using Google Gemini and Groq.
- **Data Visualization:** Building complex citation network graphs on the fly.
- **Web App:** A smooth, responsive Flask backend with vanilla JS logic.

## Local Development Setup

Ready to get your hands dirty? Here is how you set up the project locally.

1. **Fork & Clone:**
   Fork the repo and clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Meta-Research.git
   cd Meta-Research
   ```

2. **Virtual Environment:**
   Create an isolated environment so dependencies don't clutter your system.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   We heavily rely on external APIs. Create a `.env` file in the root directory based on the `.env.example` structure (see the README for needed keys). To test AI features, you will at minimum need `GEMINI_API_KEY` and `GROQ_API_KEY`.

5. **Fire it up:**
   ```bash
   python3 app.py
   ```
   The Flask server and SQLite database will auto-initialize. Access it at `http://localhost:5000`.

## Architecture Overview for Nerds

If you want to understand how things connect under the hood, here is the mental model:
- **`app.py` & `routes/`:** The entry point and Flask Blueprint routers. Focus here if you are adding new endpoints or pages.
- **`services/`:** Where the heavy lifting lives. 
  - `providers/`: Code to scrape/query semantic APIs. If you want to add a new academic source (e.g., PubMed, IEEE Xplore), build a wrapper here inheriting from `services.providers.base.BaseProvider`.
  - `chat.py`: Where Gemini and Groq logic encapsulate.
- **`models.py`:** Our SQLAlchemy definitions. We use standard SQLite for simplicity.
- **`citation_graph/`:** An entirely decoupled blueprint handling graph caching and D3/Sigma JS generation.

## How to Submit Your Changes

1. **Create a Branch:**
   Never commit directly to `main`. Always create a descriptive branch:
   ```bash
   git checkout -b feature/awesome-new-provider
   # or
   git checkout -b fix/auth-bug
   ```

2. **Write Clean Code:**
   - **Backend:** Follow standard Python conventions (PEP 8). Keep changes modular in the `services/` directory rather than dumping logic into routes.
   - **Frontend:** Vanilla JS is used. Keep things lightweight and responsive.

3. **Commit Messages:**
   Write clear, concise commit messages. 
   - Good: `feat: added PubMed search provider in services`
   - Bad: `fixed some things`

4. **Push & Pull Request:**
   Push your branch and open a Pull Request against the `main` branch of the original repository.
   - Give your PR a descriptive title.
   - Briefly outline what you changed and why.
   - If UI changes were made, please attach screenshots or screen recordings!

## Where to Start?

Not sure what to work on? Here are some cool areas where help is always appreciated:
- **Optimization:** Speeding up the concurrent API calls when fetching cross-provider search results.
- **New Providers:** Adding new academic sources in `services/providers/`.
- **LLM Context:** Improving the prompt engineering for summarizations and paper chat within `services/chat.py`.
- **Frontend Polish:** Refining the responsive design, adding dark mode toggles, or sprucing up the D3 citation graph physics.

## Getting Help

If you're stuck, have questions about the architecture, or want to discuss a massive refactoring idea before writing code, feel free to open a "Discussion" issue on GitHub. 

Happy coding!