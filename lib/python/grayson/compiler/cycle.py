import logging

from pygraph.classes.graph import graph
from pygraph.classes.digraph import digraph
from pygraph.algorithms.cycles import find_cycle

logger = logging.getLogger (__name__)

class CycleDetector (object):

    def __init__(self, nodes, edges):

        self.graph = digraph ()
        
        self.graph.add_nodes (nodes)

        for edge in edges:
            logger.debug ("      %s --> %s", edge[0], edge [1])
            self.graph.add_edge (edge)

    def detect_cycle (self):
        return find_cycle (self.graph)

        
