# Archivist AI - Article Library & Smart Classifier

Archivist AI is a low-to-medium fidelity web application designed to host, display, and organize a consolidated list of articles from Pocket and Instapaper. 

The application automatically merges the articles, crawls their original web page headers in parallel, and categorizes them into 21 distinct, non-overlapping tags using the Groq Llama-3.3-70b-Versatile LLM.

## Project Structure
- `app.py`: Flask backend server providing REST API endpoints to load, search, and edit article tags.
- `process_articles.py`: Stream-based processing pipeline that parallel-crawls web pages (with a fast 1.5s timeout) and batch-classifies them via Groq.
- `templates/index.html`: A beautiful, premium, glassmorphic dark-mode UI built with Tailwind CSS and Vue.js.
- `articles_database.json`: Active JSON database storing crawl metadata and assigned tags.
- `consolidated_categorized_articles.xlsx`: The final Excel export that is automatically synchronized whenever a tag is modified in the UI or by the pipeline.

## How to Run & Use the Application

### 1. Requirements
Ensure you have the required dependencies installed in your Python environment:
```bash
pip install flask pandas openpyxl requests beautifulsoup4
```

### 2. Run the Processing Pipeline
The pipeline processes the 1,742 articles in parallel streaming blocks. It saves progress incrementally, so you can stop and resume safely at any time:
```bash
python process_articles.py
```

### 3. Start the Web Dashboard
You can run the web server while the pipeline continues to crawl and classify in the background:
```bash
python app.py
```
By default, the application is hosted locally on:
👉 **[http://localhost:5005](http://localhost:5005)**

## Features & UX Details
- **Dynamic Database Synchronization**: Edits made to tags via the Web UI are instantly saved to `articles_database.json` and exported to `consolidated_categorized_articles.xlsx`.
- **Intelligent Iframe Reader**: Clicking an article displays its live original web page inside a large viewer. If a publisher's policy blocks iframe embeds, a prominent warning bar with a quick link allows you to open it directly in a new tab.
- **Fast Block-by-Block Streaming**: Running crawling and classification in blocks of 40 ensures high-speed execution (averaging ~2.2 articles/sec) while strictly adhering to Groq API Rate Limits.
- **Search & Filters**: Search in real-time by title, URL, or tag. Filter articles by original source (Pocket vs. Instapaper) or active category.
