# Exploration & Remediation Report: Milestone M3 Iteration 2 (Hybrid RAG Robustness)

- **Agent**: `explorer_m3_iter2_2` (Read-only Explorer, Archetype: Explorer)
- **Target**: `backend/memory/hybrid_rag.py`
- **Milestone**: M3 Iteration 2 (Robustness Remediation)
- **Date**: 2026-11-10T12:27:00Z
- **Parent Conversation ID**: `0fdc9e0b-a0b4-4f46-b4f4-43817ee786b4`

---

## 1. Observation

Direct code examination and empirical reproduction of `backend/memory/hybrid_rag.py` confirmed four discrete robustness defects identified in Milestone M3 Iteration 1 Gate audits:

### 1.1 Zero-Division Risk in `compute_rrf_score`
- **Location**: `backend/memory/hybrid_rag.py:31-38`
- **Existing Code**:
  ```python
  def compute_rrf_score(rank: int, k: int = 60) -> float:
      """
      Computes Reciprocal Rank Fusion score: 1.0 / (k + rank).
      rank is 1-based (best hit = 1).
      """
      if rank <= 0:
          return 0.0
      return 1.0 / (float(k) + float(rank))
  ```
- **Observed Failure**:
  Executing `compute_rrf_score(1, k=-1)` causes `float(k) + float(rank) == 0.0`, crashing immediately:
  ```
  ZeroDivisionError: float division by zero
  ```
  Executing with `k=-5, rank=2` produces `-0.3333333333333333`, which violates RRF non-negativity invariants.

### 1.2 Path Handling in `HybridMemory.__init__`
- **Location**: `backend/memory/hybrid_rag.py:129-148`
- **Existing Code**:
  ```python
  def __init__(
      self,
      db_path: Optional[Path] = None,
      k: int = 60,
      embedding_dim: int = 384,
  ):
      self.k = k
      self.embedding_dim = embedding_dim
      self.embedder = NumpyDenseEmbedder(dim=embedding_dim)
      self.db_path = db_path or DEFAULT_MEMORY_DB_PATH
      self._lock = threading.Lock()
      ...
      if str(self.db_path) != ":memory:":
          self.db_path.parent.mkdir(parents=True, exist_ok=True)
  ```
- **Observed Failure**:
  Executing `HybridMemory(db_path="custom/storage.db")` passes a string `str`. On line 146, `self.db_path.parent` crashes:
  ```
  AttributeError: 'str' object has no attribute 'parent'
  ```

### 1.3 Windows SQLite File Handle Locks on Transaction Block Exit
- **Location**: `backend/memory/hybrid_rag.py:150, 184, 212, 346, 356`
- **Existing Code**:
  ```python
  with self._lock, sqlite3.connect(self.db_path) as conn:
      ...
  ```
- **Observed Behavior**:
  In Python's standard library `sqlite3`, using `with sqlite3.connect(...) as conn:` manages transaction commit/rollback semantics on block exit, but **does not invoke `conn.close()`**.
  On Windows (Win32 NTFS file lock subsystem), unclosed connection objects hold active kernel file locks until CPython cycles or garbage-collects the connection reference. When a temporary database file is deleted or migrated, Windows raises:
  ```
  PermissionError: [WinError 32] The process cannot access the file because it is being used by another process
  ```

### 1.4 Sequence Unpacking & Negative Indexing in `SearchResult`
- **Location**: `backend/memory/hybrid_rag.py:69-82`
- **Existing Code**:
  ```python
  def __getitem__(self, item: int) -> Any:
      """Enables tuple-like indexing: res[0] -> doc_id, res[1] -> score."""
      if item == 0:
          return self.doc_id
      elif item == 1:
          return self.score
      elif item == 2:
          return self.content
      elif item == 3:
          return self.metadata
      raise IndexError(f"SearchResult index out of range: {item}")

  def __len__(self) -> int:
      return 4
  ```
- **Observed Failure**:
  Accessing negative indices such as `res[-1]` (to obtain `metadata`) or `res[-4]` (to obtain `doc_id`) raises:
  ```
  IndexError: SearchResult index out of range: -1
  ```
  Additionally, direct sequence iteration or `tuple(res)` is not explicitly defined via `__iter__`.

---

## 2. Logic Chain

1. **RRF Denominator Guard**:
   - In RRF, rank $r \ge 1$ and smoothing parameter $k \ge 0$.
   - Any negative rank ($r \le 0$) or non-positive denominator ($k + r \le 0$) represents an invalid or non-retrieved document.
   - Guiding `if rank <= 0 or (k + rank) <= 0: return 0.0` prevents both `ZeroDivisionError` and spurious negative ranking scores, while retaining identical behavior for standard configurations ($k=60, r \ge 1$).

2. **Path Coercion**:
   - `db_path` may be provided by callers as `None`, `str`, or `pathlib.Path`.
   - Coercing `if not db_path: self.db_path = DEFAULT_MEMORY_DB_PATH elif isinstance(db_path, str): self.db_path = Path(db_path) else: self.db_path = db_path` guarantees that `self.db_path` is always a `Path` instance.
   - Checking `self._is_memory = str(self.db_path) == ":memory:"` ensures `:memory:` mode bypasses `mkdir()`, whereas directory parents (including relative paths like `Path("test.db").parent == Path(".")`) are safely created.

3. **Explicit Connection Close Context Manager**:
   - Encapsulating connection lifecycle in a dedicated `@contextmanager def _db_connection(self)` ensures every database interaction follows:
     ```python
     with self._lock:
         conn = sqlite3.connect(str(self.db_path))
         try:
             with conn:
                 yield conn
         finally:
             conn.close()
     ```
   - `with conn:` guarantees commits on normal return and rollbacks on error.
   - `finally: conn.close()` guarantees immediate file handle release on Windows regardless of GC timing, eliminating `[WinError 32]` collisions.
   - For in-memory databases (`:memory:`), a shared connection guarded by `self._lock` is maintained so that tables created in `_init_db` persist across operations.

4. **Tuple Delegation for `SearchResult`**:
   - Constructing `fields = (self.doc_id, self.score, self.content, self.metadata)` allows delegating `__getitem__` directly to tuple indexing: `return fields[item]`.
   - This automatically enables positive indexing (`0 -> doc_id`, `1 -> score`, `2 -> content`, `3 -> metadata`), negative indexing (`-1 -> metadata`, `-2 -> content`, `-3 -> score`, `-4 -> doc_id`), slicing (`res[0:2]`), and raises standard `IndexError` when out of range (`<-4` or `>3`).
   - Defining `def __iter__(self): return iter((self.doc_id, self.score, self.content, self.metadata))` provides native sequence unpacking (`doc_id, score, content, meta = res`).

---

## 3. Caveats

- **Read-Only Explorer Constraints**: In accordance with the Explorer persona, no direct source code edits were made to `backend/memory/hybrid_rag.py`. Concrete replacement files and patch files have been staged in the agent's working directory (`.agents/teamwork/explorer_m3_iter2_2/`).
- **Cold-Start Audio Pipeline**: Note that Finding 1 from the Iteration 1 Challenger handoff pertains to `backend/voice/audio_pipeline.py` (lazy `import sounddevice as sd` in `trigger_barge_in`), which is outside the scope of `hybrid_rag.py`.

---

## 4. Conclusion & Proposed Blueprint

All 4 issues have been formulated into a minimal, backward-compatible patch.

### Artifacts Created:
1. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_iter2_2\proposed_hybrid_rag.py`
2. `e:\Projects\J.A.R.V.I.S Electron App\.agents\teamwork\explorer_m3_iter2_2\hybrid_rag.patch`

### Unified Diff:
```diff
--- a/backend/memory/hybrid_rag.py
+++ b/backend/memory/hybrid_rag.py
@@ -17,6 +17,7 @@
 import sqlite3
 import threading
 import time
+from contextlib import contextmanager
 from dataclasses import dataclass, field
 from pathlib import Path
 from typing import Any, Dict, List, Optional, Tuple, Union
@@ -32,8 +33,9 @@
     """
     Computes Reciprocal Rank Fusion score: 1.0 / (k + rank).
     rank is 1-based (best hit = 1).
+    Guarded against non-positive ranks and zero/negative denominators.
     """
-    if rank <= 0:
+    if rank <= 0 or (k + rank) <= 0:
         return 0.0
     return 1.0 / (float(k) + float(rank))
 
@@ -66,20 +68,26 @@
     fts_rank: Optional[int] = None
     vector_rank: Optional[int] = None
 
-    def __getitem__(self, item: int) -> Any:
-        """Enables tuple-like indexing: res[0] -> doc_id, res[1] -> score."""
-        if item == 0:
-            return self.doc_id
-        elif item == 1:
-            return self.score
-        elif item == 2:
-            return self.content
-        elif item == 3:
-            return self.metadata
-        raise IndexError(f"SearchResult index out of range: {item}")
+    def __getitem__(self, item: Union[int, slice]) -> Any:
+        """
+        Enables tuple-like indexing and sequence unpacking:
+        res[0] / res[-4] -> doc_id
+        res[1] / res[-3] -> score
+        res[2] / res[-2] -> content
+        res[3] / res[-1] -> metadata
+        """
+        fields = (self.doc_id, self.score, self.content, self.metadata)
+        try:
+            return fields[item]
+        except (IndexError, TypeError) as exc:
+            raise IndexError(f"SearchResult index out of range: {item}") from exc
 
     def __len__(self) -> int:
         return 4
+
+    def __iter__(self):
+        """Allows direct sequence unpacking: d, s, c, m = res."""
+        return iter((self.doc_id, self.score, self.content, self.metadata))
 
 
 class NumpyDenseEmbedder:
@@ -128,26 +136,55 @@
 
     def __init__(
         self,
-        db_path: Optional[Path] = None,
+        db_path: Optional[Union[Path, str]] = None,
         k: int = 60,
         embedding_dim: int = 384,
     ):
         self.k = k
         self.embedding_dim = embedding_dim
         self.embedder = NumpyDenseEmbedder(dim=embedding_dim)
-        self.db_path = db_path or DEFAULT_MEMORY_DB_PATH
+
+        if not db_path:
+            self.db_path = DEFAULT_MEMORY_DB_PATH
+        elif isinstance(db_path, str):
+            self.db_path = Path(db_path)
+        else:
+            self.db_path = db_path
+
         self._lock = threading.Lock()
+        self._is_memory = str(self.db_path) == ":memory:"
+        self._shared_conn: Optional[sqlite3.Connection] = None
 
         # In-memory vector index cache: doc_id -> np.ndarray
         self._vectors: Dict[str, np.ndarray] = {}
         self._docs: Dict[str, Dict[str, Any]] = {}
 
-        if str(self.db_path) != ":memory:":
+        if not self._is_memory:
             self.db_path.parent.mkdir(parents=True, exist_ok=True)
         self._init_db()
 
+    @contextmanager
+    def _db_connection(self):
+        """
+        Thread-safe context manager managing SQLite transaction lifecycle
+        and guaranteeing immediate, explicit connection closing on Windows.
+        """
+        with self._lock:
+            if self._is_memory:
+                if self._shared_conn is None:
+                    self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
+                with self._shared_conn:
+                    yield self._shared_conn
+            else:
+                conn = sqlite3.connect(str(self.db_path))
+                try:
+                    with conn:
+                        yield conn
+                finally:
+                    conn.close()
+
     def _init_db(self):
-        with self._lock, sqlite3.connect(self.db_path) as conn:
+        with self._db_connection() as conn:
             conn.execute("PRAGMA journal_mode = WAL")
             conn.execute("""
                 CREATE TABLE IF NOT EXISTS memory_docs (
@@ -164,7 +201,6 @@
                     tokenize='trigram'
                 )
             """)
-            conn.commit()
 
     def index_text(
         self,
@@ -181,7 +217,7 @@
         meta_str = json.dumps(meta)
 
         # 1. Update SQLite and FTS5
-        with self._lock, sqlite3.connect(self.db_path) as conn:
+        with self._db_connection() as conn:
             conn.execute(
                 "INSERT OR REPLACE INTO memory_docs (id, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                 (doc_id, text, meta_str, now),
@@ -191,7 +227,6 @@
             except Exception:
                 pass
             conn.execute("INSERT INTO memory_fts (id, content) VALUES (?, ?)", (doc_id, text))
-            conn.commit()
 
         # 2. Update In-Memory cache & Vector index
         vec = self.embedder.embed(text)
@@ -209,7 +244,7 @@
             return []
 
         hits: List[Tuple[str, int]] = []
-        with self._lock, sqlite3.connect(self.db_path) as conn:
+        with self._db_connection() as conn:
             cur = conn.cursor()
             try:
                 # FTS5 ranked match
@@ -343,19 +378,27 @@
 
     def delete_document(self, doc_id: str) -> bool:
         """Removes a document from both stores."""
-        with self._lock, sqlite3.connect(self.db_path) as conn:
+        with self._db_connection() as conn:
             conn.execute("DELETE FROM memory_docs WHERE id = ?", (doc_id,))
             conn.execute("DELETE FROM memory_fts WHERE id = ?", (doc_id,))
-            conn.commit()
         self._vectors.pop(doc_id, None)
         self._docs.pop(doc_id, None)
         return True
 
     def clear(self) -> None:
         """Clears all indexed documents."""
-        with self._lock, sqlite3.connect(self.db_path) as conn:
+        with self._db_connection() as conn:
             conn.execute("DELETE FROM memory_docs")
             conn.execute("DELETE FROM memory_fts")
-            conn.commit()
         self._vectors.clear()
         self._docs.clear()
+
+    def close(self) -> None:
+        """Explicitly closes any persistent shared in-memory connection."""
+        with self._lock:
+            if self._shared_conn is not None:
+                try:
+                    self._shared_conn.close()
+                except Exception:
+                    pass
+                self._shared_conn = None
```

---

## 5. Verification Method

To independently verify this proposed remediation:

1. **Verify All 4 Fixes Against Isolated Adversarial Probes**:
   ```powershell
   python -c "
   import sys, importlib.util
   spec = importlib.util.spec_from_file_location('backend.memory.hybrid_rag', '.agents/teamwork/explorer_m3_iter2_2/proposed_hybrid_rag.py')
   mod = importlib.util.module_from_spec(spec)
   sys.modules['backend.memory.hybrid_rag'] = mod
   spec.loader.exec_module(mod)

   # Probe 1: Zero-division guard
   assert mod.compute_rrf_score(1, k=-1) == 0.0
   assert mod.compute_rrf_score(0, k=60) == 0.0
   assert mod.compute_rrf_score(-5, k=60) == 0.0

   # Probe 2: String db_path handling
   import tempfile, os
   td = tempfile.mkdtemp()
   str_db = os.path.join(td, 'sub', 'test.db')
   hm = mod.HybridMemory(db_path=str_db)
   hm.index_text('doc1', 'quantum neural interface')
   res = hm.search('quantum', top_k=1)
   assert len(res) == 1 and res[0].doc_id == 'doc1'

   # Probe 3: Windows handle release
   hm.clear()
   del hm
   os.remove(str_db) # Passes with zero WinError 32

   # Probe 4: SearchResult negative indexing and tuple unpacking
   sr = mod.SearchResult('docX', 'content text', 0.99, {'author': 'stark'})
   assert sr[-1] == {'author': 'stark'}
   assert sr[-2] == 'content text'
   assert sr[-3] == 0.99
   assert sr[-4] == 'docX'
   d, s, c, m = sr
   assert (d, s, c, m) == ('docX', 0.99, 'content text', {'author': 'stark'})
   print('ALL 4 PROPOSALS VERIFIED WITH 100% SUCCESS!')
   "
   ```

2. **Verify Against Existing Test Suites**:
   ```powershell
   python -c "
   import sys, importlib.util, unittest
   spec = importlib.util.spec_from_file_location('backend.memory.hybrid_rag', '.agents/teamwork/explorer_m3_iter2_2/proposed_hybrid_rag.py')
   mod = importlib.util.module_from_spec(spec)
   sys.modules['backend.memory.hybrid_rag'] = mod
   spec.loader.exec_module(mod)

   loader = unittest.TestLoader()
   suite1 = loader.loadTestsFromName('tests.test_adversarial_m3')
   suite2 = loader.loadTestsFromName('tests.e2e.test_tier1_features.TestTier1Milestone3Features')
   runner = unittest.TextTestRunner(verbosity=1)
   res = runner.run(unittest.TestSuite([suite1, suite2]))
   assert res.wasSuccessful()
   "
   ```
   *Expected Result*: `Ran 70 tests ... OK`

3. **Verify Forensics Benchmark Throughput**:
   ```powershell
   python tests/benchmark_m3_forensics.py
   ```
   *Expected Result*: 10,000-doc Cosine Similarity Search Time $\le 2\text{ms}$.
