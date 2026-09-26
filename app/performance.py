"""Medições leves da sessão para a tela de Diagnóstico."""

from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
import math
import os
import sys
from threading import Lock
from time import perf_counter
from typing import Callable, Iterator, ParamSpec, TypeVar


METRIC_LABELS = (
    "Abertura até janela pronta",
    "Montagem da janela",
    "Benchmark local",
    "Benchmark Fribbels",
    "Planejador",
    "Importação · leitura e rede",
    "Importação · gravação",
)


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    count: int
    last_ms: float
    average_ms: float
    minimum_ms: float
    maximum_ms: float


class PerformanceMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._values: dict[str, tuple[int, float, float, float, float]] = {}

    def record(self, label: str, seconds: float) -> None:
        if label not in METRIC_LABELS or not math.isfinite(seconds) or seconds < 0:
            return
        milliseconds = seconds * 1000
        with self._lock:
            count, _last, total, minimum, maximum = self._values.get(
                label, (0, 0.0, 0.0, milliseconds, milliseconds)
            )
            self._values[label] = (
                count + 1, milliseconds, total + milliseconds,
                min(minimum, milliseconds), max(maximum, milliseconds),
            )

    def record_duration(self, label: str, started_at: float) -> None:
        self.record(label, perf_counter() - started_at)

    @contextmanager
    def time(self, label: str) -> Iterator[None]:
        started_at = perf_counter()
        try:
            yield
        finally:
            self.record_duration(label, started_at)

    def snapshot(self) -> dict[str, MetricSnapshot]:
        with self._lock:
            return {
                label: MetricSnapshot(count, last, total / count, minimum, maximum)
                for label, (count, last, total, minimum, maximum)
                in self._values.items()
            }


PERFORMANCE = PerformanceMetrics()

P = ParamSpec("P")
R = TypeVar("R")


def measured(label: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with PERFORMANCE.time(label):
                return function(*args, **kwargs)
        return wrapper
    return decorate


def process_memory_bytes() -> int | None:
    """Conjunto residente atual do processo, quando o sistema o informa."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            get_process = ctypes.windll.kernel32.GetCurrentProcess
            get_process.restype = wintypes.HANDLE
            get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
            get_memory.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD,
            ]
            get_memory.restype = wintypes.BOOL
            handle = get_process()
            if get_memory(
                handle, ctypes.byref(counters), counters.cb
            ):
                return int(counters.WorkingSetSize)
        except (AttributeError, OSError, ValueError):
            return None
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/self/statm", encoding="ascii") as statm:
                resident_pages = int(statm.read().split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE")
        except (OSError, IndexError, ValueError):
            return None
    return None


def format_duration(milliseconds: float) -> str:
    if milliseconds >= 1000:
        return f"{milliseconds / 1000:.2f} s"
    if milliseconds >= 10:
        return f"{milliseconds:.0f} ms"
    return f"{milliseconds:.1f} ms"


def diagnostic_lines(metrics: PerformanceMetrics = PERFORMANCE) -> list[str]:
    snapshot = metrics.snapshot()
    memory = process_memory_bytes()
    lines = [
        "DESEMPENHO DESTA SESSÃO",
        "Tempos de tentativas concluídas, inclusive falhas; média desde a abertura.",
        f"Memória residente do processo: {memory / (1024 * 1024):.1f} MiB"
        if memory is not None else "Memória residente do processo: indisponível",
    ]
    for label in METRIC_LABELS:
        sample = snapshot.get(label)
        if sample is None:
            lines.append(f"{label}: ainda não medido")
        else:
            count_label = "medição" if sample.count == 1 else "medições"
            lines.append(
                f"{label}: último {format_duration(sample.last_ms)} · "
                f"média {format_duration(sample.average_ms)} · "
                f"máximo {format_duration(sample.maximum_ms)} · "
                f"{sample.count} {count_label}"
            )
    observed_operations = [
        (label, snapshot[label]) for label in METRIC_LABELS[2:]
        if label in snapshot
    ]
    if observed_operations:
        slowest_label, slowest = max(
            observed_operations, key=lambda item: item[1].average_ms
        )
        lines.append(
            f"Maior média observada: {slowest_label} "
            f"({format_duration(slowest.average_ms)})."
        )
    return lines
