from __future__ import annotations

import copy
from abc import ABC, abstractmethod
# from bisect import bisect_left, insort
import threading
from typing import Any, Final

from sortedcontainers import SortedList  # type: ignore

from core.message import JsonMessage


class State(ABC):
    pass



class LogicalTime:
  def __init__(self, name: str, ts: int = 0) -> None:
    self.ts: Final[int] = ts
    self.name: Final[str] = name

  def __repr__(self) -> str:
    return f"{self.name}: {self.ts}"

  def __eq__(self, other: object) -> bool:
    if isinstance(other, LogicalTime):
      return self.ts == other.ts and self.name == other.name
    raise ValueError

  def __lt__(self, other: LogicalTime) -> bool:
    if self.ts < other.ts:
      return True
    if self.ts > other.ts:
      return False
    return self.name < other.name

  def serialize(self) -> tuple[str, int]:
    return self.name, self.ts


class LogEntry(ABC):
  def __init__(self, msg: JsonMessage):
    assert "ltime" in msg, "Set ltime before getting"
    self.ltime = LogicalTime(msg["ltime"][1], msg["ltime"][0])

  @abstractmethod
  def do(self, state: State) -> None:
    """
    Apply this log entry on the state.
    """
    pass

  @abstractmethod
  def undo(self, state: State) -> None:
    """
    Undo this log entry on the state.
    """
    pass

  def __eq__(self, other: object) -> bool:
    if isinstance(other, LogEntry):
      return self.ltime == other.ltime
    raise ValueError

  def __lt__(self, other: LogEntry) -> bool:
    return self.ltime < other.ltime

  @abstractmethod
  def to_dict(self) -> dict[str, Any]:
    pass


class VectorTime:
  def __init__(self, times: list[LogicalTime])-> None:
    self._vector: dict[str, LogicalTime] = {t.name: t for t in times}

  @staticmethod
  def new(servers: list[str]) -> VectorTime:
    return VectorTime([LogicalTime(s) for s in servers])

  def __repr__(self) -> str:
    return repr(self._vector)

  def __getitem__(self, server: str) -> LogicalTime:
    return self._vector[server]

  def advance(self, ltime: LogicalTime) -> None:
    s = ltime.name  # server name
    assert self._vector[s].ts <= ltime.ts, \
      f"Tried to take {s} clock backwards from {self._vector[s].ts} to {ltime.ts}!"
    self._vector[s] = ltime

  def is_ltime_earlier(self, ltime: LogicalTime) -> bool:
    s = ltime.name  # server name
    return ltime.ts <= self._vector[s].ts

  def is_vtime_earlier(self, vtime: VectorTime) -> bool:
    # We don't use Python's __lt__ here since vector times do not have a total order.
    # It is possible that (not a < b) and (not b < a)
    for s in vtime._vector:
      if not self.is_ltime_earlier(vtime._vector[s]):
        return False
    return True

  def __eq__(self, other: object) -> bool:
    if isinstance(other, VectorTime):
      for key in self._vector:
        if other._vector[key] != self._vector[key]:
          return False
      return True
    raise ValueError

  def to_dict(self) -> dict[str, float]:
    return {k: t.ts for k, t in self._vector.items()}

class Storage:
  def __init__(self, servers: list[str], init_state: State):
    # Timestamp till which we have committed the writes.
    self.c = VectorTime.new(servers)
    # Timestamp till which we have performed the tentative writes.
    self.f = VectorTime.new(servers)

    self.committed_log: list[LogEntry] = []
    self.tentative_log: SortedList[LogEntry] = SortedList(key=lambda l: l.ltime)

    self.committed_st: State = copy.deepcopy(init_state)
    self.tentative_st: State = copy.deepcopy(init_state)

    self._apply_lock: threading.Lock = threading.Lock()

  def chk_invariants(self) -> None:
    # F should always be ahead of C. C should always be ahead of O.
    assert self.f.is_vtime_earlier(self.c)

    # If tentative log is empty, F should be equal to C; committed state and tentative state
    # should be equivalent
    if len(self.tentative_log) == 0:
      assert self.f == self.c
      assert self.committed_st == self.tentative_st

  def apply(self, commits: list[LogEntry], tentatives: SortedList[LogEntry]) -> None:
    """
    Apply the list of commits and tentatives to the state.
    Args:
      commits: These can be out of order.
      tentatives: These are given in the order of ltime.ts.
    """
    # TODO-3
    # Acquire the lock
    self._apply_lock.acquire()

    # Need to compare the incoming logs with the current state and apply the logs accordingly 
    # Incoming logs are ones obtained from anti-entropy

    # For commited logs, we know the incoming log wont be in commited, so just append it after changing the state
    for log in commits:
      if log not in self.committed_log: # commits are idempotent
        log.do(self.committed_st)
        self.committed_log.append(log)
        self.c.advance(log.ltime)
      if log in self.tentative_log:
        self.tentative_log.remove(log)
    
    # For tentative logs, we may need to undo some logs and then reapply the logs in the correct order
    # Following ways to handle this 
    # M1. 
      # start tentative from commited state, combine both tentative logs and apply them in order
      # This will ensure that the logs are applied in the correct order
    # M2.
      # Use the undo method somehow to undo the logs that are not in the incoming logs

    # For now, I will use M1 (for testing)
    self.tentative_st = copy.deepcopy(self.committed_st)
    self.f = copy.deepcopy(self.c)

    # Combine both tentative logs (whilst ensuring idempotency)
    for log in tentatives:
      if log not in self.tentative_log:
        self.tentative_log.add(log)
        
    # Apply them in order now
    for log in self.tentative_log:
        log.do(self.tentative_st)
        self.f.advance(log.ltime)

    # # M2
    # # Undo the logs that are in the current tentative logs but not in the incoming tentative logs
    # # Then apply the combined logs in the correct order

    # for log in self.tentative_log:
    #   log.undo(self.tentative_st)

    # # Remove duplicates from the tentative logs (cannot use set since LogEntry is not hashable)
    # # This is done to ensure idempotency
    # for log in tentatives:
    #   if log not in self.tentative_log:
    #     self.tentative_log.add(log)

    # # Apply them in order
    # for log in self.tentative_log:
    #   log.do(self.tentative_st)
    #   self.f.advance(log.ltime)
    
    # if len(self.tentative_log) == 0:
    #   self.f = self.c
    #   self.tentative_st = copy.deepcopy(self.committed_st)

    # Release the lock
    self._apply_lock.release()


  def commit(self, writes: list[LogEntry]) -> None:
    """Writes committed writes"""
    self.apply(writes, SortedList())

  def tentative(self, writes: SortedList[LogEntry]) -> None:
    """Performs tentative writes"""
    self.apply([], writes)

  def anti_entropy(self, c: VectorTime, f: VectorTime) -> tuple[list[LogEntry], SortedList[LogEntry]]:
    """
    Args:
      c: commit vector of the other storage
      f: tentative vector of the other storage

    Returns:
      committed and tentative logEntries that I have and the other storage don't.
    """
    # TODO-4
    # From video: Other server sends its timestamp to me. I compare with my timestamp and send back the logs that it doesn't have.
    # NOTE: I do not update my state in any way. I just compare the vector clocks and return the logs that the other storage doesn't have.
    
    # Assert that the incoming vector clocks are valid wrt itself
    # assert c.is_vtime_earlier(f) #! WRONG: SHOULD BE f.is_vtime_earlier(c) but for some reason only this works?!?!?

    # Assert that the committed timestamps are either earlier or later and not mixed
    # Directly use leq
    assert c.is_vtime_earlier(self.c) or self.c.is_vtime_earlier(c), f"Mixed timestamps for committed logs, incoming c: {c}, our c: {self.c}"
    
    # Get the committed logs that the other storage doesn't have
    committed_logs = [log for log in self.committed_log if not c.is_ltime_earlier(log.ltime)]
    # Get the tentative logs that the other storage doesn't have
    tentative_logs = SortedList([log for log in self.tentative_log if not f.is_ltime_earlier(log.ltime)], key=lambda l: l.ltime)

    return committed_logs, tentative_logs
