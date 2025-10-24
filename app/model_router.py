"""
Smart Model Router - Selects best model based on task, budget, leaderboard
"""
import sqlite3
from typing import Optional, Dict, List
from datetime import datetime
import json

class ModelRouter:
    """Intelligent model selection based on task type and budget"""

    def __init__(self, db_path: str = "data/models.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize models database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT,
                rank INTEGER,
                score REAL,
                price_input REAL,
                price_output REAL,
                context_length INTEGER,
                task_scores TEXT,  -- JSON: {"coding": 95, "reasoning": 90}
                is_free BOOLEAN DEFAULT 0,
                updated_at TIMESTAMP
            )
        """)

        # Free models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS free_models (
                model_id TEXT PRIMARY KEY,
                available BOOLEAN DEFAULT 1,
                last_checked TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models(model_id)
            )
        """)

        # Default free models (bootstrapping)
        defaults = [
            ("deepseek/deepseek-r1:free", "DeepSeek R1", "DeepSeek", 5, 92.0, 0, 0, 64000, '{"coding":95,"reasoning":90}', 1),
            ("google/gemini-2.0-flash-exp:free", "Gemini 2.0 Flash", "Google", 8, 88.0, 0, 0, 1000000, '{"coding":85,"reasoning":88}', 1),
            ("nousresearch/hermes-3-llama-3.1-405b:free", "Hermes 3 405B", "NousResearch", 12, 85.0, 0, 0, 128000, '{"coding":90,"reasoning":87}', 1),
        ]

        for model in defaults:
            cursor.execute("""
                INSERT OR IGNORE INTO models
                (model_id, name, provider, rank, score, price_input, price_output, context_length, task_scores, is_free)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, model)

            cursor.execute("""
                INSERT OR IGNORE INTO free_models (model_id, available, last_checked)
                VALUES (?, 1, ?)
            """, (model[0], datetime.utcnow()))

        conn.commit()
        conn.close()

    def get_best_model(
        self,
        task_type: str = "coding",
        budget: str = "free",
        min_context: int = 32000
    ) -> Dict:
        """
        Select best model for task

        Args:
            task_type: "coding", "reasoning", "creative", "fast"
            budget: "free", "cheap" (<$1/1M), "balanced" (<$5/1M), "premium"
            min_context: Minimum context length required

        Returns:
            {"model_id": str, "name": str, "score": float}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query based on budget
        if budget == "free":
            query = """
                SELECT m.model_id, m.name, m.score, m.task_scores
                FROM models m
                JOIN free_models f ON m.model_id = f.model_id
                WHERE m.is_free = 1
                  AND f.available = 1
                  AND m.context_length >= ?
                ORDER BY m.rank ASC
                LIMIT 1
            """
        else:
            price_limit = {"cheap": 1.0, "balanced": 5.0, "premium": 999.0}[budget]
            query = """
                SELECT model_id, name, score, task_scores
                FROM models
                WHERE price_input <= ?
                  AND context_length >= ?
                ORDER BY rank ASC
                LIMIT 1
            """
            cursor.execute(query, (price_limit, min_context))

        if budget == "free":
            cursor.execute(query, (min_context,))

        result = cursor.fetchone()
        conn.close()

        if result:
            task_scores = json.loads(result[3]) if result[3] else {}
            return {
                "model_id": result[0],
                "name": result[1],
                "overall_score": result[2],
                "task_score": task_scores.get(task_type, result[2])
            }

        # Fallback to DeepSeek R1 Free
        return {
            "model_id": "deepseek/deepseek-r1:free",
            "name": "DeepSeek R1 (Free)",
            "overall_score": 92.0,
            "task_score": 95.0 if task_type == "coding" else 90.0
        }

    def list_available_models(self, free_only: bool = True) -> List[Dict]:
        """List all available models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if free_only:
            query = """
                SELECT m.model_id, m.name, m.provider, m.context_length, m.score
                FROM models m
                JOIN free_models f ON m.model_id = f.model_id
                WHERE m.is_free = 1 AND f.available = 1
                ORDER BY m.rank ASC
            """
        else:
            query = """
                SELECT model_id, name, provider, context_length, score
                FROM models
                ORDER BY rank ASC
                LIMIT 20
            """

        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()

        return [
            {
                "model_id": r[0],
                "name": r[1],
                "provider": r[2],
                "context": f"{r[3]//1000}K" if r[3] else "?",
                "score": r[4]
            }
            for r in results
        ]

    def update_free_models(self, model_ids: List[str]):
        """Update list of available free models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Mark all as unavailable
        cursor.execute("UPDATE free_models SET available = 0")

        # Mark provided models as available
        for model_id in model_ids:
            cursor.execute("""
                INSERT OR REPLACE INTO free_models (model_id, available, last_checked)
                VALUES (?, 1, ?)
            """, (model_id, datetime.utcnow()))

        conn.commit()
        conn.close()
