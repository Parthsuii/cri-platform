from __future__ import annotations

import json
import urllib.request
import urllib.error
import hashlib
from typing import Any

class BeliefStore:
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "beliefs") -> None:
        self.qdrant_url = f"http://{host}:{port}"
        self.collection_name = collection_name
        self.vector_size = 384
        
        # Initialize sentence transformer model
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.use_fallback_embeddings = False
        except Exception as exc:
            print(f"Warning: failed to load SentenceTransformer: {exc}. Using deterministic fallback embeddings.")
            self.model = None
            self.use_fallback_embeddings = True

    def get_embedding(self, text: str) -> list[float]:
        if self.use_fallback_embeddings or not self.model:
            # Generate deterministic 384-dimensional fallback embeddings using SHA-256 hashes
            emb = []
            for i in range(self.vector_size):
                h = hashlib.sha256(f"{text}-{i}".encode("utf-8")).digest()
                emb.append(float(h[0]) / 255.0 - 0.5)
            return emb
        
        # Real sentence embeddings
        vector = self.model.encode(text)
        return [float(x) for x in vector]

    def _request(self, path: str, method: str = "GET", data: dict | None = None) -> dict:
        url = f"{self.qdrant_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"} if body else {},
            method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            # Check if 404/etc.
            try:
                err_body = json.loads(err.read().decode("utf-8"))
                return {"error": err_body}
            except Exception:
                return {"error": str(err)}
        except Exception as exc:
            return {"error": str(exc)}

    def create_collection_if_not_exists(self) -> bool:
        res = self._request(f"/collections/{self.collection_name}")
        if "error" not in res:
            return True # Already exists
        
        # Create it
        payload = {
            "vectors": {
                "size": self.vector_size,
                "distance": "Cosine"
            }
        }
        create_res = self._request(f"/collections/{self.collection_name}", method="PUT", data=payload)
        return "error" not in create_res

    def upsert_belief(self, belief_id: str, belief_text: str, confidence: float = 0.9, metadata: dict | None = None) -> bool:
        self.create_collection_if_not_exists()
        
        # Generate deterministic integer ID from belief_id string
        hashed_id = int(hashlib.md5(belief_id.encode("utf-8")).hexdigest(), 16) % (2**63 - 1)
        vector = self.get_embedding(belief_text)
        
        payload = {
            "points": [
                {
                    "id": hashed_id,
                    "vector": vector,
                    "payload": {
                        "belief_id": belief_id,
                        "belief": belief_text,
                        "confidence": confidence,
                        "metadata": metadata or {}
                    }
                }
            ]
        }
        
        res = self._request(f"/collections/{self.collection_name}/points?wait=true", method="PUT", data=payload)
        return "error" not in res

    def search_beliefs(self, query_text: str, limit: int = 3) -> list[dict[str, Any]]:
        self.create_collection_if_not_exists()
        vector = self.get_embedding(query_text)
        
        payload = {
            "vector": vector,
            "limit": limit,
            "with_payload": True
        }
        
        res = self._request(f"/collections/{self.collection_name}/points/search", method="POST", data=payload)
        if "error" in res:
            print(f"Qdrant search error: {res['error']}")
            return []
        
        results = []
        for hit in res.get("result", []):
            payload_data = hit.get("payload", {})
            results.append({
                "belief_id": payload_data.get("belief_id"),
                "belief": payload_data.get("belief"),
                "confidence": payload_data.get("confidence", 0.0),
                "score": hit.get("score", 0.0),
                "metadata": payload_data.get("metadata", {})
            })
        return results
