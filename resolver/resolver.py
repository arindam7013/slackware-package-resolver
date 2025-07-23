import json
import networkx as nx
from pysat.solvers import Glucose3
from itertools import combinations

class Resolver:
    def __init__(self, db_path='database.json'):
        """Initializes the resolver by loading the package database."""
        with open(db_path, 'r') as f:
            self.db = json.load(f)
        self.graph = self._build_dependency_graph()

    def _build_dependency_graph(self):
        """Builds a directed graph from the dependency database."""
        G = nx.DiGraph()
        for package, details in self.db.items():
            G.add_node(package)
            for dependency in details.get('requires', []):
                G.add_edge(package, dependency)
        return G

    def resolve_with_topsort(self, packages_to_install):
        """
        Resolves dependencies using a simple topological sort.
        Fails if there are any circular dependencies.
        """
        nodes_to_include = set()
        for pkg in packages_to_install:
            if pkg not in self.graph:
                raise ValueError(f"Package '{pkg}' not found in the database.")
            nodes_to_include.add(pkg)
            nodes_to_include.update(nx.descendants(self.graph, pkg))
        
        subgraph = self.graph.subgraph(nodes_to_include)
        try:
            # The networkx topological_sort gives packages with no dependencies first.
            # We must reverse the list to get the correct installation order.
            install_order = list(nx.topological_sort(subgraph))
            install_order.reverse()
            return install_order
        except nx.NetworkXUnfeasible:
            raise RuntimeError("Topological sort failed. The request contains a circular dependency.")

    def resolve_with_sat(self, packages_to_install):
        """
        Resolves dependencies using a SAT solver for complex cases.
        """
        pkg_to_int = {pkg: i + 1 for i, pkg in enumerate(self.db.keys())}
        int_to_pkg = {i + 1: pkg for i, pkg in enumerate(self.db.keys())}
        
        clauses = []

        for pkg in packages_to_install:
            if pkg not in pkg_to_int:
                raise ValueError(f"Package '{pkg}' not found in the database.")
            clauses.append([pkg_to_int[pkg]])

        for pkg, details in self.db.items():
            for dep in details.get('requires', []):
                if dep in pkg_to_int: # Ensure dependency exists in db
                    clauses.append([-pkg_to_int[pkg], pkg_to_int[dep]])
        
        base_packages = {}
        for pkg, details in self.db.items():
            base = details.get("base_package")
            if base:
                base_packages.setdefault(base, []).append(pkg)
        
        for base, versions in base_packages.items():
            for v1, v2 in combinations(versions, 2):
                clauses.append([-pkg_to_int[v1], -pkg_to_int[v2]])

        with Glucose3(bootstrap_with=clauses) as solver:
            if solver.solve():
                model = solver.get_model()
                solution_packages = [int_to_pkg[i] for i in model if i > 0]
                
                # Topologically sort the final result for correct install order
                subgraph = self.graph.subgraph(solution_packages)
                install_order = list(nx.topological_sort(subgraph))
                install_order.reverse()
                return install_order
            else:
                # Logic to generate a detailed conflict report
                conflict_report = "SAT solver found a conflict!\n"
                from collections import defaultdict
                deps_of_requests = {}
                for pkg in packages_to_install:
                    deps = nx.descendants(self.graph, pkg)
                    deps.add(pkg)
                    deps_of_requests[pkg] = deps
                base_conflicts = defaultdict(list)
                for pkg, deps in deps_of_requests.items():
                    for dep in deps:
                        base = self.db.get(dep, {}).get("base_package")
                        if base:
                            base_conflicts[base].append(f"'{dep}' (required by '{pkg}')")
                for base, sources in base_conflicts.items():
                    if len(set(sources)) > 1:
                        conflict_report += f"  - Reason: Multiple versions of '{base}' are required.\n"
                        for source in sorted(list(set(sources))):
                            conflict_report += f"    - {source}\n"
                raise RuntimeError(conflict_report)

    def list_packages(self):
        """Returns a sorted list of all available package names."""
        return sorted(self.db.keys())

    def explain(self, package_name):
        """Generates a human-readable explanation of the dependency tree."""
        if package_name not in self.graph:
            raise ValueError(f"Package '{package_name}' not found in the database.")
        nodes_to_include = nx.descendants(self.graph, package_name)
        nodes_to_include.add(package_name)
        subgraph = self.graph.subgraph(nodes_to_include)
        lines = []
        self._print_tree(subgraph, package_name, lines)
        return "\n".join(lines)

    def _print_tree(self, tree, node, lines, prefix="", is_last=True):
        """Recursively builds the tree string for the explanation."""
        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{node}")
        children = list(tree.successors(node))
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            self._print_tree(tree, child, lines, prefix=new_prefix, is_last=(i == len(children) - 1))