"""Coding Evaluation Adapter for EvalHub.

Evaluates LLM coding ability on HumanEval+ and MBPP+ benchmarks.
Generates code completions via vLLM, executes tests via mcp-code-sandbox
(air-gap safe — no HF_ALLOW_CODE_EVAL needed).
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from evalhub.adapter import (
    ErrorInfo,
    EvaluationResult,
    FrameworkAdapter,
    JobCallbacks,
    JobPhase,
    JobResults,
    JobSpec,
    JobStatus,
    JobStatusUpdate,
    MessageInfo,
)

logger = logging.getLogger(__name__)

BENCHMARKS = {
    "humaneval_plus": {
        "name": "HumanEval+",
        "loader": "get_human_eval_plus",
        "style": "completion",
    },
    "mbpp_plus": {
        "name": "MBPP+",
        "loader": "get_mbpp_plus",
        "style": "solution",
    },
}

MCP_SANDBOX_URL = os.getenv(
    "MCP_SANDBOX_URL", "http://mcp-code-sandbox.mcp-servers.svc:3005"
)
SANDBOX_CONCURRENCY = int(os.getenv("SANDBOX_CONCURRENCY", "10"))


class CodingEvalAdapter(FrameworkAdapter):
    """Evaluates coding ability via EvalPlus benchmarks + mcp-code-sandbox."""

    def run_benchmark_job(self, config: JobSpec, callbacks: JobCallbacks) -> JobResults:
        start_time = time.time()
        benchmark_id = config.benchmark_id
        logger.info(f"Starting coding eval job {config.id} for {benchmark_id}")

        self._trace_enabled = os.getenv("ENABLE_TRACING", "true").lower() == "true"
        self._trace_records: list[dict] = []

        try:
            callbacks.report_status(JobStatusUpdate(
                status=JobStatus.RUNNING, phase=JobPhase.INITIALIZING, progress=0.0,
                message=MessageInfo(message=f"Initializing {benchmark_id}", message_code="initializing"),
            ))

            if benchmark_id not in BENCHMARKS:
                raise ValueError(f"Unknown benchmark: {benchmark_id}. Available: {list(BENCHMARKS.keys())}")

            bench = BENCHMARKS[benchmark_id]
            model_url = config.model.url
            model_name = config.model.name
            params = config.parameters or {}
            concurrency = params.get("concurrency", 5)
            temperature = params.get("temperature", 0.0)
            max_tokens = params.get("max_tokens", 1024)
            sandbox_timeout = params.get("sandbox_timeout", 15)
            num_examples = params.get("num_examples") or config.num_examples

            # --- Load problems ---
            callbacks.report_status(JobStatusUpdate(
                status=JobStatus.RUNNING, phase=JobPhase.LOADING_DATA, progress=0.1,
                message=MessageInfo(message=f"Loading {bench['name']} problems", message_code="loading_data"),
            ))
            problems = self._load_problems(benchmark_id, num_examples)
            total = len(problems)
            logger.info(f"Loaded {total} problems for {benchmark_id}")

            # --- Evaluate ---
            callbacks.report_status(JobStatusUpdate(
                status=JobStatus.RUNNING, phase=JobPhase.RUNNING_EVALUATION, progress=0.2,
                message=MessageInfo(message=f"Evaluating {total} problems via {model_name}", message_code="running_evaluation"),
            ))

            results_rows = asyncio.run(self._evaluate_async(
                problems, benchmark_id, model_url, model_name,
                temperature, max_tokens, concurrency, sandbox_timeout,
                callbacks, total,
            ))

            # --- Metrics ---
            callbacks.report_status(JobStatusUpdate(
                status=JobStatus.RUNNING, phase=JobPhase.POST_PROCESSING, progress=0.9,
                message=MessageInfo(message="Computing pass@1", message_code="post_processing"),
            ))
            evaluation_results, pass1 = self._compute_metrics(results_rows, benchmark_id)
            self._save_artifacts(config.id, benchmark_id, model_name, results_rows, pass1)

            duration = time.time() - start_time
            return JobResults(
                id=config.id,
                benchmark_id=benchmark_id,
                benchmark_index=config.benchmark_index,
                model_name=model_name,
                results=evaluation_results,
                overall_score=pass1 / 100.0 if pass1 is not None else None,
                num_examples_evaluated=total,
                duration_seconds=duration,
                completed_at=datetime.now(UTC),
                evaluation_metadata={
                    "framework": "coding-eval",
                    "benchmark": benchmark_id,
                    "concurrency": concurrency,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        except Exception as e:
            logger.exception("Coding evaluation failed")
            callbacks.report_status(JobStatusUpdate(
                status=JobStatus.FAILED,
                message=MessageInfo(message=str(e), message_code="failed"),
                error=ErrorInfo(message=str(e), message_code="evaluation_error"),
            ))
            raise

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_problems(self, benchmark_id: str, limit: int | None = None) -> list[dict]:
        from evalplus.data import get_human_eval_plus, get_mbpp_plus

        raw = get_human_eval_plus() if benchmark_id == "humaneval_plus" else get_mbpp_plus()
        problems = []
        for task_id, p in raw.items():
            problems.append({
                "task_id": task_id,
                "prompt": p["prompt"],
                "entry_point": p["entry_point"],
                "canonical_solution": p.get("canonical_solution", p.get("code", "")),
                "test": p.get("test", ""),
                "test_list": p.get("test_list", []),
                "test_setup_code": p.get("test_setup_code", ""),
            })
        if limit and limit < len(problems):
            problems = problems[:limit]
        return problems

    # ------------------------------------------------------------------
    # Async evaluation
    # ------------------------------------------------------------------

    async def _evaluate_async(
        self, problems, benchmark_id, model_url, model_name,
        temperature, max_tokens, concurrency, sandbox_timeout,
        callbacks, total,
    ) -> list[dict]:
        base_url = model_url.rstrip("/")
        for suffix in ("/v1/chat/completions", "/v1/completions", "/v1"):
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
                break

        is_humaneval = benchmark_id == "humaneval_plus"
        llm_sem = asyncio.Semaphore(concurrency)
        sandbox_sem = asyncio.Semaphore(SANDBOX_CONCURRENCY)
        completed_count = 0
        last_reported = 0

        async def eval_one(llm_client: httpx.AsyncClient, problem: dict) -> dict:
            nonlocal completed_count, last_reported
            task_id = problem["task_id"]

            if is_humaneval:
                sys_msg = (
                    "Complete the following Python function. "
                    "Output ONLY the function body (properly indented). "
                    "No explanation, no markdown fences."
                )
                user_msg = problem["prompt"]
            else:
                sys_msg = (
                    "Write the Python function described below. "
                    "Output ONLY the complete function definition. "
                    "No explanation, no markdown fences."
                )
                user_msg = problem["prompt"]

            try:
                async with llm_sem:
                    completion = await self._call_llm(
                        llm_client, model_name, sys_msg, user_msg,
                        temperature, max_tokens,
                    )
            except Exception as e:
                logger.error(f"LLM failed for {task_id}: {e}")
                completion = ""

            if not completion.strip():
                completed_count += 1
                return {"task_id": task_id, "passed": False, "completion": "", "error": "empty"}

            test_code = self._build_test_script(problem, completion, is_humaneval)

            async with sandbox_sem:
                passed, exec_out = await self._execute_test(test_code, sandbox_timeout)

            completed_count += 1
            interval = max(1, total // 10)
            if completed_count - last_reported >= interval:
                last_reported = completed_count
                callbacks.report_status(JobStatusUpdate(
                    status=JobStatus.RUNNING, phase=JobPhase.RUNNING_EVALUATION,
                    progress=0.2 + 0.7 * (completed_count / total),
                    message=MessageInfo(
                        message=f"Evaluated {completed_count}/{total}", message_code="running_evaluation",
                    ),
                ))

            return {
                "task_id": task_id,
                "passed": passed,
                "completion": completion[:500],
                "exec_output": exec_out[:500] if exec_out else "",
            }

        per_task_timeout = sandbox_timeout + max_tokens // 5 + 60

        async def eval_one_safe(llm_client: httpx.AsyncClient, problem: dict) -> dict:
            try:
                return await asyncio.wait_for(
                    eval_one(llm_client, problem), timeout=per_task_timeout,
                )
            except asyncio.TimeoutError:
                nonlocal completed_count
                completed_count += 1
                logger.warning(f"Task {problem['task_id']} timed out ({per_task_timeout}s)")
                return {"task_id": problem["task_id"], "passed": False, "completion": "", "error": "task_timeout"}

        async with httpx.AsyncClient(
            base_url=base_url, verify=False,
            timeout=httpx.Timeout(connect=10, read=300, write=10, pool=30),
            limits=httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency),
        ) as llm_client:
            tasks = [eval_one_safe(llm_client, p) for p in problems]
            results = await asyncio.gather(*tasks)

        return list(results)

    # ------------------------------------------------------------------
    # Test script construction
    # ------------------------------------------------------------------

    def _build_test_script(self, problem: dict, completion: str, is_humaneval: bool) -> str:
        completion = self._sanitize_code(completion)

        if is_humaneval:
            entry = problem["entry_point"]
            if completion.lstrip().startswith("def "):
                solution = completion
            else:
                solution = problem["prompt"] + completion
            return f"{solution}\n\n{problem['test']}\n\ncheck({entry})\n"
        else:
            setup = problem.get("test_setup_code") or ""
            assertions = "\n".join(problem.get("test_list", []))
            return f"{setup}\n\n{completion}\n\n{assertions}\n"

    @staticmethod
    def _sanitize_code(code: str) -> str:
        lines = code.strip().split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Sandbox execution via MCP Streamable HTTP
    # ------------------------------------------------------------------

    async def _execute_test(self, code: str, timeout: int = 30) -> tuple[bool, str]:
        overall_timeout = timeout + 30
        try:
            return await asyncio.wait_for(
                self._execute_test_inner(code, timeout), timeout=overall_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Sandbox overall timeout ({overall_timeout}s)")
            return False, f"overall timeout ({overall_timeout}s)"
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return False, str(e)

    async def _execute_test_inner(self, code: str, timeout: int) -> tuple[bool, str]:
        async with httpx.AsyncClient(
            base_url=MCP_SANDBOX_URL,
            timeout=httpx.Timeout(connect=5, read=timeout + 10, write=5, pool=10),
        ) as client:
            hdrs = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            init_resp = await client.post("/mcp", headers=hdrs, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "coding-eval", "version": "1.0"},
                },
            })
            sid = init_resp.headers.get("mcp-session-id")
            if sid:
                hdrs["Mcp-Session-Id"] = sid
            await client.post("/mcp", headers=hdrs, json={
                "jsonrpc": "2.0", "method": "notifications/initialized",
            })
            resp = await client.post("/mcp", headers=hdrs, json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {
                    "name": "execute_code",
                    "arguments": {"code": code, "language": "python", "timeout": timeout},
                },
            })

        text = self._parse_mcp_result_text(resp)
        passed = "[python] OK" in text
        return passed, text

    @staticmethod
    def _parse_mcp_result_text(resp: httpx.Response) -> str:
        ct = resp.headers.get("content-type", "")
        if "text/event-stream" in ct:
            for line in resp.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "result" in data and data["result"].get("content"):
                            return data["result"]["content"][0].get("text", "")
                    except json.JSONDecodeError:
                        continue
            return resp.text[:300]

        try:
            data = resp.json()
            if "result" in data and data["result"].get("content"):
                return data["result"]["content"][0].get("text", "")
            return json.dumps(data)[:300]
        except Exception:
            return resp.text[:300]

    # ------------------------------------------------------------------
    # LLM call with retry
    # ------------------------------------------------------------------

    async def _call_llm(
        self, client: httpx.AsyncClient, model: str,
        sys_msg: str, user_msg: str, temperature: float, max_tokens: int,
    ) -> str:
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if os.getenv("DISABLE_THINKING", "true").lower() == "true":
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        max_retries = 5
        for attempt in range(max_retries):
            try:
                r = await client.post("/v1/chat/completions", json=payload)
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"].strip()
                if self._trace_enabled:
                    self._trace_records.append({
                        "prompt": user_msg[:500], "response": content[:500],
                        "model": model, "status": "success",
                    })
                return content

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 500, 503) and attempt < max_retries - 1:
                    delay = min(60, (2 ** attempt)) + random.uniform(0, 2)
                    logger.warning(f"HTTP {e.response.status_code}, retry {attempt+1}/{max_retries} in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"LLM API error: {e}")
                return ""

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
                logger.error(f"LLM connection error after retries: {e}")
                return ""

            except Exception as e:
                logger.error(f"Unexpected LLM error: {e}")
                return ""
        return ""

    # ------------------------------------------------------------------
    # Metrics & artifacts
    # ------------------------------------------------------------------

    def _compute_metrics(self, rows: list[dict], benchmark_id: str):
        total = len(rows)
        passed = sum(1 for r in rows if r["passed"])
        pass1 = round(passed / total * 100, 2) if total else 0.0

        results = [EvaluationResult(
            metric_name=f"{benchmark_id}_pass1",
            metric_value=pass1,
            metric_type="accuracy",
            num_samples=total,
            metadata={"passed": passed, "failed": total - passed},
        )]
        return results, pass1

    def _save_artifacts(self, job_id, benchmark_id, model_name, rows, pass1):
        out = Path(self.local_jobs_base_path or "/tmp/coding-eval-results") / "results"
        out.mkdir(parents=True, exist_ok=True)

        with open(out / "results.json", "w") as f:
            json.dump({
                "job_id": job_id, "benchmark_id": benchmark_id,
                "model_name": model_name, "pass_at_1": pass1,
                "total": len(rows), "passed": sum(1 for r in rows if r["passed"]),
                "details": rows,
            }, f, indent=2)

        with open(out / "RESULTS.md", "w") as f:
            p = sum(1 for r in rows if r["passed"])
            f.write(f"# {benchmark_id} Results\n\n")
            f.write(f"**Model**: {model_name}  \n**pass@1**: {pass1}%  \n**Passed**: {p}/{len(rows)}\n")


# ======================================================================
# Entry point
# ======================================================================

def main() -> None:
    import sys
    from evalhub.adapter import DefaultCallbacks

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        job_spec_path = os.getenv("EVALHUB_JOB_SPEC_PATH", "/meta/job.json")
        adapter = CodingEvalAdapter(job_spec_path=job_spec_path)
        logger.info(f"Job {adapter.job_spec.id}  benchmark={adapter.job_spec.benchmark_id}")

        callbacks = DefaultCallbacks.from_adapter(adapter)
        results = adapter.run_benchmark_job(adapter.job_spec, callbacks)
        logger.info(f"pass@1 = {results.overall_score}")

        try:
            run_id = callbacks.mlflow.save(results, adapter.job_spec)
            if run_id:
                results.mlflow_run_id = run_id
                logger.info(f"MLflow run: {run_id}")
        except Exception as e:
            logger.warning(f"MLflow save failed (non-fatal): {e}")
            run_id = None

        mlflow_uri = os.getenv("MLFLOW_DIRECT_URI", "https://mlflow.redhat-ods-applications.svc:8443")
        if adapter._trace_enabled and adapter._trace_records and run_id:
            try:
                import mlflow
                from mlflow import MlflowClient
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                os.environ.pop("MLFLOW_TRACKING_SERVER_CERT_PATH", None)
                os.environ["MLFLOW_TRACKING_URI"] = mlflow_uri
                os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

                sa_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
                if Path(sa_path).exists():
                    os.environ["MLFLOW_TRACKING_TOKEN"] = Path(sa_path).read_text().strip()

                mlflow.set_tracking_uri(mlflow_uri)
                mc = MlflowClient(tracking_uri=mlflow_uri)
                exp_id = mc.get_run(run_id).info.experiment_id

                logged = 0
                for i, rec in enumerate(adapter._trace_records[:20]):
                    try:
                        span = mc.start_trace(
                            name=f"code_gen_{i}", experiment_id=exp_id,
                            inputs={"prompt": rec["prompt"], "model": rec["model"]},
                        )
                        mc.end_trace(
                            trace_id=span.request_id,
                            outputs={"response": rec["response"]},
                            attributes={"status": rec["status"]},
                        )
                        logged += 1
                    except Exception:
                        break
                logger.info(f"Logged {logged} traces to MLflow")
            except Exception as e:
                logger.warning(f"MLflow tracing failed (non-fatal): {e}")

        try:
            callbacks.report_results(results)
        except Exception as e:
            logger.warning(f"report_results failed (non-fatal): {e}")
        sys.exit(0)

    except Exception:
        logger.exception("Job failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
