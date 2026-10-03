# ai-generated: 85% - Claude Code generated the metrics engine, I validated against METRIC-SPEC.md rules R-01 to R-21

"""DORA metrics computation engine (METRIC-SPEC.md)."""

from datetime import datetime, timezone
from typing import Any, Optional
from statistics import median as stats_median

# Constants
PRODUCTION = "production"
WINDOW_DAYS = 21.0
SECONDS_PER_DAY = 86400


def parse_rfc3339(dt_str: str) -> datetime:
    """Parse RFC 3339 string to datetime."""
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))


def round_duration(seconds: float) -> int:
    """Round duration to whole seconds (half-up)."""
    return int(seconds + 0.5)


def round_ratio(ratio: float) -> float:
    """Round ratio to 6 decimal places (half-up)."""
    return round(ratio, 6)


def median_or_none(values: list) -> Optional[int]:
    """Compute median of values or None if empty."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return round_duration(stats_median(values))


def clamp_zero(value: float) -> float:
    """Clamp negative values to zero."""
    return max(0.0, value)


class DoraMetricsEngine:
    """Compute DORA metrics from event log."""
    
    def __init__(self, events: list, window: dict):
        self.raw_events = events
        self.window_from = parse_rfc3339(window["from"])
        self.window_to = parse_rfc3339(window["to"])
        
        # Deduplicate events by event_id (R-05: first occurrence wins)
        seen_ids = set()
        self.events = []
        for event in events:
            if event.get("event_id") not in seen_ids:
                self.events.append(event)
                seen_ids.add(event.get("event_id"))
        
        # Organize events by type
        self.commits = {}  # sha -> commit event
        self.deployments = {}  # deployment_id -> deployment event
        self.incidents = {}  # incident_id -> list of incidents
        
        self._organize_events()
        
        # Validate well-formedness
        self._validate_wellformedness()
        
        # Track anomalies and counts
        self.anomalies = {
            "negative_lead_time_pairs": 0,
            "deployments_without_commits": 0,
            "commits_never_on_main": 0,
            "revert_chains_collapsed": 0,
            "overlapping_incident_pairs": 0,
        }
        self.counts = {
            "deployments": 0,
            "successful_deployments": 0,
            "failed_deployments": 0,
            "recovered_failures": 0,
            "open_failures": 0,
            "rework_deployments": 0,
            "lead_time_pairs": 0,
            "changes": 0,
        }
    
    def _organize_events(self):
        """Organize events by type."""
        for event in self.events:
            event_type = event.get("type")
            
            if event_type == "commit":
                self.commits[event["sha"]] = event
            elif event_type == "deployment":
                self.deployments[event["deployment_id"]] = event
            elif event_type == "incident":
                incident_id = event["incident_id"]
                if incident_id not in self.incidents:
                    self.incidents[incident_id] = {}
                phase = event["phase"]
                self.incidents[incident_id][phase] = event
    
    def _validate_wellformedness(self):
        """Validate log is well-formed (before organize_events uses the data)."""
        # Check all shas are unique
        shas = set()
        for commit in [e for e in self.events if e.get("type") == "commit"]:
            sha = commit.get("sha")
            if sha in shas:
                raise ValueError(f"duplicate sha: {sha}")
            shas.add(sha)
        
        # Check reverts, commits, caused_by, deployments reference existing events
        for event in self.events:
            # Check reverts
            if event.get("type") == "commit" and event.get("reverts"):
                if event["reverts"] not in shas:
                    raise ValueError(f"reverts {event['reverts']} not found in log")
            
            # Check deployment commits
            if event.get("type") == "deployment":
                for sha in event.get("commits", []):
                    if sha not in shas:
                        raise ValueError(f"deployment references unknown sha: {sha}")
                
                # Check caused_by references incident
                if event.get("caused_by"):
                    caused_by_incident = event["caused_by"]
                    found = False
                    for e in self.events:
                        if e.get("type") == "incident" and e.get("incident_id") == caused_by_incident:
                            found = True
                            break
                    if not found:
                        raise ValueError(f"caused_by {caused_by_incident} not found in log")
            
            # Check incident deployments
            if event.get("type") == "incident":
                for dep_id in event.get("deployments", []):
                    found = False
                    for e in self.events:
                        if e.get("type") == "deployment" and e.get("deployment_id") == dep_id:
                            found = True
                            break
                    if not found:
                        raise ValueError(f"incident references unknown deployment: {dep_id}")
        
        # Check each incident_id has at most one opened and one resolved
        incident_phases = {}
        for event in self.events:
            if event.get("type") == "incident":
                incident_id = event.get("incident_id")
                phase = event.get("phase")
                if incident_id not in incident_phases:
                    incident_phases[incident_id] = set()
                if phase in incident_phases[incident_id]:
                    raise ValueError(f"incident {incident_id} has multiple {phase} events")
                incident_phases[incident_id].add(phase)
    
    def _resolve_change_id(self, sha: str) -> Optional[str]:
        """Resolve change_id following revert chain (R-06)."""
        commit = self.commits.get(sha)
        if not commit:
            return None
        
        change_id = commit.get("change_id")
        if change_id is None:
            # This is a revert, follow the chain
            reverts_sha = commit.get("reverts")
            if reverts_sha:
                return self._resolve_change_id(reverts_sha)
        
        return change_id
    
    def _get_first_commit_instant(self, change_id: str) -> datetime:
        """Get first commit instant for a change (R-07)."""
        min_at = None
        for commit in self.commits.values():
            if self._resolve_change_id(commit["sha"]) == change_id:
                commit_at = parse_rfc3339(commit["at"])
                if min_at is None or commit_at < min_at:
                    min_at = commit_at
        return min_at
    
    def compute(self) -> dict:
        """Compute all DORA metrics."""
        # Count revert commits (E2) - R-06
        self.anomalies["revert_chains_collapsed"] = sum(
            1 for commit in self.commits.values() 
            if commit.get("reverts") is not None
        )
        
        # Filter production deployments in window
        production_deployments = [
            dep for dep in self.deployments.values()
            if dep.get("environment") == PRODUCTION
            and self.window_from <= parse_rfc3339(dep["at"]) < self.window_to
        ]
        
        # Compute counts
        self.counts["deployments"] = len(production_deployments)
        successful = [d for d in production_deployments if d.get("outcome") == "success"]
        failed = [d for d in production_deployments if d.get("outcome") == "failure"]
        
        self.counts["successful_deployments"] = len(successful)
        self.counts["failed_deployments"] = len(failed)
        
        # Count deployments without commits (R-10)
        for dep in production_deployments:
            if not dep.get("commits"):
                self.anomalies["deployments_without_commits"] += 1
        
        # R-08: change_lead_time_seconds_p50
        lead_times = self._compute_lead_times(successful)
        change_lead_time = median_or_none(lead_times)
        self.counts["lead_time_pairs"] = len(lead_times)
        
        # R-11: deployment_frequency_per_day
        window_length_days = (self.window_to - self.window_from).total_seconds() / SECONDS_PER_DAY
        deployment_frequency = len(production_deployments) / window_length_days if window_length_days > 0 else 0
        deployment_frequency = round_ratio(deployment_frequency)
        
        # R-12: failed_deployment_recovery_time_seconds_p50
        recovery_times = self._compute_recovery_times(failed)
        failed_deployment_recovery_time = median_or_none(recovery_times)
        
        # R-14: change_fail_rate
        change_fail_rate = None
        if self.counts["deployments"] > 0:
            change_fail_rate = round_ratio(self.counts["failed_deployments"] / self.counts["deployments"])
        
        # R-15: deployment_rework_rate
        rework_count = sum(1 for d in production_deployments 
                          if d.get("unplanned") and d.get("caused_by"))
        self.counts["rework_deployments"] = rework_count
        deployment_rework_rate = None
        if self.counts["deployments"] > 0:
            deployment_rework_rate = round_ratio(rework_count / self.counts["deployments"])
        
        # Ground truth metrics
        changes_delivered = self._count_changes_delivered(successful)
        true_lead_time = self._compute_true_lead_time(successful)
        
        self.counts["changes"] = len(set(
            self._resolve_change_id(commit["sha"]) 
            for commit in self.commits.values()
            if self._resolve_change_id(commit["sha"]) is not None
        ))
        
        return {
            "spec_version": "1.0.0",
            "window": {
                "from": self.window_from.isoformat().replace('+00:00', 'Z'),
                "to": self.window_to.isoformat().replace('+00:00', 'Z'),
            },
            "deployment_frequency_per_day": deployment_frequency,
            "change_lead_time_seconds_p50": change_lead_time,
            "failed_deployment_recovery_time_seconds_p50": failed_deployment_recovery_time,
            "change_fail_rate": change_fail_rate,
            "deployment_rework_rate": deployment_rework_rate,
            "counts": self.counts,
            "anomalies": self.anomalies,
            "ground_truth": {
                "changes_delivered": changes_delivered,
                "true_change_lead_time_seconds_p50": true_lead_time,
            },
        }
    
    def _compute_lead_times(self, successful_deployments: list) -> list:
        """Compute lead times for successful deployments (R-08, R-09, R-10)."""
        lead_times = []
        commits_never_on_main = set()
        
        for dep in successful_deployments:
            dep_at = parse_rfc3339(dep["at"])
            
            for sha in dep.get("commits", []):
                commit = self.commits.get(sha)
                if not commit:
                    continue
                
                # Check branch (R-09 anomaly)
                if commit.get("branch") != "main":
                    commits_never_on_main.add(sha)
                
                commit_at = parse_rfc3339(commit["at"])
                lead_time_sec = (dep_at - commit_at).total_seconds()
                
                # R-03: clamp negative to zero
                if lead_time_sec < 0:
                    lead_time_sec = 0
                    self.anomalies["negative_lead_time_pairs"] += 1
                
                lead_times.append(round_duration(lead_time_sec))
        
        self.anomalies["commits_never_on_main"] = len(commits_never_on_main)
        return lead_times
    
    def _compute_recovery_times(self, failed_deployments: list) -> list:
        """Compute recovery times for failed deployments (R-12, R-13)."""
        recovery_times = []
        open_failures = 0
        
        # Check for overlapping incidents
        incident_list = []
        for incident_id, phases in self.incidents.items():
            if "opened" in phases:
                incident_list.append({
                    "id": incident_id,
                    "opened": parse_rfc3339(phases["opened"]["at"]),
                    "resolved": parse_rfc3339(phases["resolved"]["at"]) if "resolved" in phases else self.window_to,
                })
        
        # Count overlapping incident pairs (R-13)
        overlapping = 0
        for i in range(len(incident_list)):
            for j in range(i + 1, len(incident_list)):
                a = incident_list[i]
                b = incident_list[j]
                if a["opened"] < b["resolved"] and b["opened"] < a["resolved"]:
                    overlapping += 1
        self.anomalies["overlapping_incident_pairs"] = overlapping
        
        # Compute recovery for each failed deployment
        for dep in failed_deployments:
            dep_id = dep["deployment_id"]
            dep_at = parse_rfc3339(dep["at"])
            
            # Find covering incident (R-12)
            covering = None
            for incident_id, phases in self.incidents.items():
                if "opened" in phases:
                    if dep_id in phases["opened"].get("deployments", []):
                        incident_opened = parse_rfc3339(phases["opened"]["at"])
                        if covering is None or incident_opened < parse_rfc3339(covering["opened"]["at"]):
                            covering = {
                                "opened": phases["opened"]["at"],
                                "resolved": phases["resolved"]["at"] if "resolved" in phases else None,
                            }
            
            if covering and covering["resolved"]:
                resolved_at = parse_rfc3339(covering["resolved"])
                recovery_time = (resolved_at - dep_at).total_seconds()
                recovery_time = clamp_zero(recovery_time)
                recovery_times.append(round_duration(recovery_time))
                self.counts["recovered_failures"] += 1
            else:
                open_failures += 1
        
        self.counts["open_failures"] = open_failures
        return recovery_times
    
    def _count_changes_delivered(self, successful_deployments: list) -> int:
        """Count distinct changes delivered (R-16)."""
        changes = set()
        for dep in successful_deployments:
            for sha in dep.get("commits", []):
                change_id = self._resolve_change_id(sha)
                if change_id:
                    changes.add(change_id)
        return len(changes)
    
    def _compute_true_lead_time(self, successful_deployments: list) -> Optional[int]:
        """Compute true change lead time (R-17)."""
        changes = {}
        
        for dep in successful_deployments:
            dep_at = parse_rfc3339(dep["at"])
            
            for sha in dep.get("commits", []):
                change_id = self._resolve_change_id(sha)
                if change_id:
                    if change_id not in changes:
                        first_commit_at = self._get_first_commit_instant(change_id)
                        if first_commit_at:
                            lead_time = (dep_at - first_commit_at).total_seconds()
                            lead_time = clamp_zero(lead_time)
                            changes[change_id] = round_duration(lead_time)
        
        if not changes:
            return None
        
        return median_or_none(list(changes.values()))
