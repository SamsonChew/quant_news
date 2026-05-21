CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  authors TEXT NOT NULL,
  published_at TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  abstract TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,
  tags TEXT NOT NULL,
  language TEXT NOT NULL,
  metadata TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_collected_at ON items(collected_at);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_source_type ON items(source_type);

CREATE TABLE IF NOT EXISTS summaries (
  item_id TEXT PRIMARY KEY,
  one_line_summary TEXT NOT NULL,
  technical_summary TEXT NOT NULL,
  key_points TEXT NOT NULL,
  quant_relevance TEXT NOT NULL,
  possible_use_case TEXT NOT NULL,
  limitations TEXT NOT NULL,
  read_priority TEXT NOT NULL,
  model_name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS scores (
  item_id TEXT PRIMARY KEY,
  relevance_score REAL NOT NULL,
  novelty_score REAL NOT NULL,
  academic_score REAL NOT NULL,
  discussion_score REAL NOT NULL,
  actionable_score REAL NOT NULL,
  final_score REAL NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS reports (
  report_date TEXT PRIMARY KEY,
  report_path TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  item_count INTEGER NOT NULL,
  source_stats TEXT NOT NULL
);
