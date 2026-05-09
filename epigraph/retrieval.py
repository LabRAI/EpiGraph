from collections import defaultdict, deque
from typing import Dict, Iterable, List, Tuple

import networkx as nx

from .common import normalize_text, read_json


class EpiGraphRetriever:
    """PPR-style graph retriever matching the paper's Graph-RAG setting."""

    def __init__(
        self,
        triplets_path: str,
        ppr_alpha: float = 0.15,
        max_subgraph_nodes: int = 30,
        max_paths: int = 12,
    ) -> None:
        self.triplets = read_json(triplets_path)
        self.ppr_alpha = ppr_alpha
        self.max_subgraph_nodes = max_subgraph_nodes
        self.max_paths = max_paths
        self.graph = nx.DiGraph()
        self.entity_names: Dict[str, str] = {}
        self.entity_to_edges: Dict[str, List[dict]] = defaultdict(list)
        self._build()

    def _build(self) -> None:
        for row in self.triplets:
            head = normalize_text(row.get("head", "")).lower()
            tail = normalize_text(row.get("tail", "")).lower()
            if not head or not tail:
                continue
            self.entity_names.setdefault(head, row.get("head", head))
            self.entity_names.setdefault(tail, row.get("tail", tail))
            weight = max(float(row.get("paper_count", 1)), 1.0)
            self.graph.add_edge(
                head,
                tail,
                relation=row.get("relation", "related_to"),
                weight=weight,
                paper_count=row.get("paper_count", 1),
                evidence=row.get("evidence", row.get("paper_ids", [])),
            )
            self.entity_to_edges[head].append(row)
            self.entity_to_edges[tail].append(row)

    def retrieve(self, query: str) -> Dict[str, object]:
        seeds = self.match_entities(query)
        if not seeds:
            return {"seeds": [], "paths": [], "triplets": []}
        scores = nx.pagerank(
            self.graph,
            alpha=1 - self.ppr_alpha,
            personalization={node: 1.0 for node in seeds},
            weight="weight",
            max_iter=100,
        )
        keep = {
            node
            for node, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[
                : self.max_subgraph_nodes
            ]
        }
        keep.update(seeds)
        subgraph = self.graph.subgraph(keep).copy()
        paths = self.serialize_paths(subgraph, seeds)
        return {
            "seeds": [self.entity_names.get(s, s) for s in seeds],
            "paths": paths,
            "triplets": self._triplets_from_subgraph(subgraph),
        }

    def match_entities(self, query: str) -> List[str]:
        q = f" {query.lower()} "
        hits = []
        for entity in self.entity_names:
            if len(entity) < 3:
                continue
            if f" {entity} " in q or entity.replace("-", " ") in q:
                hits.append(entity)
        return hits[:8]

    def serialize_paths(self, subgraph: nx.DiGraph, seeds: Iterable[str]) -> List[str]:
        paths: List[Tuple[float, str]] = []
        for seed in seeds:
            if seed not in subgraph:
                continue
            queue = deque([(seed, [seed], 0)])
            while queue:
                node, nodes, depth = queue.popleft()
                if depth >= 4:
                    continue
                for nxt in subgraph.successors(node):
                    if nxt in nodes:
                        continue
                    edge = subgraph[node][nxt]
                    new_nodes = nodes + [nxt]
                    text = self._format_path(subgraph, new_nodes)
                    score = sum(
                        subgraph[a][b].get("paper_count", 1)
                        for a, b in zip(new_nodes[:-1], new_nodes[1:])
                    )
                    paths.append((score, text))
                    queue.append((nxt, new_nodes, depth + 1))
        dedup = {}
        for score, text in paths:
            dedup[text] = max(score, dedup.get(text, 0))
        return [
            text
            for text, _ in sorted(dedup.items(), key=lambda item: item[1], reverse=True)[
                : self.max_paths
            ]
        ]

    def _format_path(self, graph: nx.DiGraph, nodes: List[str]) -> str:
        pieces = [self.entity_names.get(nodes[0], nodes[0])]
        for a, b in zip(nodes[:-1], nodes[1:]):
            rel = graph[a][b].get("relation", "related_to")
            pc = graph[a][b].get("paper_count", 1)
            pieces.append(f"--{rel} [{pc} papers]--> {self.entity_names.get(b, b)}")
        return " ".join(pieces)

    def _triplets_from_subgraph(self, subgraph: nx.DiGraph) -> List[dict]:
        rows = []
        for h, t, data in subgraph.edges(data=True):
            rows.append(
                {
                    "head": self.entity_names.get(h, h),
                    "relation": data.get("relation", "related_to"),
                    "tail": self.entity_names.get(t, t),
                    "paper_count": data.get("paper_count", 1),
                }
            )
        return rows

