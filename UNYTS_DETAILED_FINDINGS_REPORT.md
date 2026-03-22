# Unyts Memory Spike Investigation Report

Date: 2026-03-22
Project under test: SimPandas (consuming local Unyts checkout)
Unyts path observed in runtime: D:/git/unyts/src/unyts

## 1. Executive Summary
A severe RAM spike was reproduced during test execution, including machine hangs reported at full 64 GB usage.

Detailed investigation found no recursive pytest process loop in SimPandas tests. The dominant risk appears in Unyts initialization behavior on Python 3.14, specifically the parallel build and fallback logic in database initialization.

A defensive mitigation was applied in SimPandas to disable Unyts 3.14 parallel startup by default, after which full test runs completed reliably.

## 2. Environment and Scope
- OS: Windows
- Python: 3.14
- SimPandas branch: development
- Unyts source used: local development checkout (not PyPI wheel)

Investigation goal:
- Determine whether RAM growth was due to test-loop process spawning, leaked Python child processes, or heavy in-process computation.

## 3. Symptoms Observed
- User observed full system memory consumption and machine hang during full pytest.
- Prior session showed single Python processes reaching very high memory usage.
- Controlled reruns showed one main heavy Python process and no unbounded process count growth.

## 4. Methodology
1) Process forensics
- Enumerate active python processes and resident memory.
- Track max process count and max working set during pytest.

2) Code-path scan
- Search SimPandas tests and source for subprocess spawning, recursive pytest launches, infinite loops, multiprocessing patterns.

3) Unyts source inspection
- Inspect initialization and parallel build logic in Unyts database and helper modules.
- Identify potential duplicate execution of heavy builders.

4) Mitigation validation
- Apply safe startup policy in SimPandas bootstrap.
- Re-run targeted and full test suites.
- Re-measure peak memory.

## 5. Key Findings

### Finding A: No recursive pytest spawning loop in SimPandas
- pytest.main calls exist in some test files but are guarded by if __name__ == '__main__'.
- During monitored full runs, python process count remained bounded (max observed: 3 including idle shells).

Conclusion:
- The crash pattern is not explained by runaway process spawning in SimPandas tests.

### Finding B: Unyts initialization is the heavy memory hotspot
Source evidence points to Unyts database initialization path:
- File: D:/git/unyts/src/unyts/database.py
- Area: PARALLEL_3_14 decision block and create_functions execution

Observed logic:
- On Python 3.14, PARALLEL_3_14 defaults to True unless overridden by env var UNYTS_PARALLEL_3_14=0.
- In PARALLEL_3_14 mode, parallel_execute(create_functions) is attempted.
- On exception, fallback starts heavy background threads and then iterates create_functions again without skipping the heavy function already started in a thread.

This differs from the non-PARALLEL branch, which explicitly skips heavy functions already running in threads.

Risk implication:
- Duplicate heavy execution during failure fallback can significantly inflate memory usage.

### Finding C: Parallel helper is aggressive by default worker count
- File: D:/git/unyts/src/unyts/helpers/_parallel_helpers.py
- parallel_execute uses ThreadPoolExecutor with max_workers up to min(len(functions), os.cpu_count()).

On many-core systems, this can schedule many heavy creators concurrently, increasing peak memory pressure.

### Finding D: Unyts lazy loading still triggers heavy build when units/converter paths are used
- File: D:/git/unyts/src/unyts/__init__.py
- Unyts uses lazy loading, but any import path requiring units/conversion triggers database load/build.

For test workloads that import SimPandas and touch units early, heavy init can occur near startup.

## 6. Measured Data
Controlled full-suite memory probe after mitigation:
- Command pattern: launch pytest in child process and sample working set periodically.
- Result:
  - Exit code: 0
  - Peak memory observed: approximately 5181.6 MB
  - Max python process count observed: 3

Interpretation:
- No process explosion.
- Memory is heavy but bounded under safe startup policy.

## 7. SimPandas-Side Mitigation Applied
Mitigation commit in SimPandas:
- Commit: f868c8d
- File changed: src/simpandas/__init__.py
- Change: set default environment variable before Unyts import path activation:
  - os.environ.setdefault('UNYTS_PARALLEL_3_14', '0')

Result:
- Full test suite passes.
- Machine-hang scenario was not reproduced during controlled reruns.

## 8. Recommended Unyts Fixes (Priority Order)

### Priority 1: Fix duplicate heavy execution in PARALLEL_3_14 fallback
In database.py exception fallback branch:
- Keep heavy tasks in one place.
- If _create_ProductivityIndex thread is started, skip that function in loop execution.
- Ensure _complete_products is not redundantly executed.

Expected effect:
- Eliminates accidental duplicate heavy builder work.

### Priority 2: Make Python 3.14 parallel startup opt-in
Current behavior defaults to True on 3.14.
Recommendation:
- Default PARALLEL_3_14 to False.
- Enable only when UNYTS_PARALLEL_3_14=1 is explicit.

Expected effect:
- Safer default for memory-constrained or unstable environments.

### Priority 3: Cap parallel workers for heavy startup builders
In _parallel_helpers.parallel_execute:
- Cap max_workers to a small upper bound (for example 2 to 4) for startup build tasks.

Expected effect:
- Reduces peak RAM pressure and thread contention.

### Priority 4: Add initialization lock and idempotence guard
- Add module-level lock for init path.
- If init is already running, wait for completion rather than starting another full build.

Expected effect:
- Prevents concurrent duplicate initialization in edge import timing cases.

## 9. Suggested Regression Tests in Unyts
1) Fallback branch single-execution test
- Simulate parallel_execute failure.
- Assert _create_ProductivityIndex is executed exactly once.

2) Worker cap behavior test
- Verify startup path does not exceed configured max workers.

3) Repeated import/init idempotence test
- Multiple imports in same process do not rebuild simultaneously.

4) Stress smoke test
- Python 3.14 full initialization completes under bounded memory threshold in CI profile.

## 10. Minimal Patch Direction (High-Level)
- In database.py fallback after parallel failure:
  - start heavy threads once
  - in create_functions loop, continue when fn is _create_ProductivityIndex (and any other already-running heavy function)
- In parallel helper:
  - bound default workers for startup heavy path
- In PARALLEL_3_14 toggle:
  - require explicit opt-in for True

## 11. Final Assessment
Root cause is most likely in Unyts startup orchestration under Python 3.14 parallel mode and failure fallback behavior, not in SimPandas test recursion.

SimPandas now includes a safe operational guard, but a source-level Unyts fix is strongly recommended to remove the hazard at origin.
