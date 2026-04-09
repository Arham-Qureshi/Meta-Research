# Meta-Research

Meta-Research is a comprehensive, AI-powered web platform designed for academic literature search, analysis, and management. It provides researchers, students, and academics with an intelligent workspace to discover papers, visualize citation networks, and directly interact with research content using advanced Large Language Models (LLMs).

## Features

- **Advanced Academic Search:** Unified search across major academic databases (arXiv, Crossref, OpenAlex, Semantic Scholar).
- **AI-Powered Paper Chat:** Interactively chat with research papers using Groq (Llama) and Google Generative AI (Gemini) to ask questions, extract insights, and get summaries.
- **Citation Graph Visualizations:** Dynamically generate and visualize citation graphs to discover connections between research papers.
- **Library Management:** Save papers, organize them into custom collections, and manage bookmarks.
- **Personalized Dashboard:** Track search history, recently viewed papers, and manage your academic profile.
- **Academic News:** Stay updated with the latest in technology and research.
- **User Authentication:** Secure user registration and login system.

## Technology Stack

- **Backend:** Python, Flask
- **Database:** SQLite (via Flask-SQLAlchemy)
- **Authentication:** Flask-Login, Werkzeug (Password Hashing)
- **AI Models:** Groq API, Google Generative AI (Gemini API)
- **Natural Language Processing:** Sumy (for local text summarization)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Jinja2 Templates

## Getting Started

Follow these instructions to set up the project locally.

### Prerequisites

- Python 3.8+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Arham-Qureshi/Meta-Research.git
   cd Meta-Research
   ```

2. **Set up a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  
   ```

3. **Install the dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory and add the necessary API keys:
   ```env
   SECRET_KEY=your_secure_flask_secret_key
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   GNEWS_API_KEY=your_gnews_api_key_here
   NEWSDATA_API_KEY=your_newsdata_api_key_here
   ```

5. **Initialize Database and Run the App**
   ```bash
   python3 app.py
   ```
   The application will automatically create the SQLite database (`meta_research.db`) and start running at `http://127.0.0.1:5000/`.

## Project Structure

```
Meta-Research/
├── app.py                      # Main application entry point
├── models.py                   # SQLAlchemy database models
├── extensions.py               # Flask extensions initialization
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (API Keys)
├── routes/                     # Blueprint routes (auth, search, chat, etc.)
├── services/                   # Business logic (API integrations, AI chat)
│   ├── providers/              # Academic API integrations (Arxiv, OpenAlex, etc.)
├── citation_graph/             # Citation graph visualizer module
├── static/                     # Static assets (CSS, JS, Images)
└── templates/                  # Jinja2 HTML templates
```

## Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check out the issues page.

## License

This project is open-source and available under the terms of the MIT License.
