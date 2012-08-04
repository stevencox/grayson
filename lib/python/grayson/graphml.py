#!/usr/bin/python

import os
import sys
import xml.sax
import urllib2
import logging
import traceback
import re

logger = logging.getLogger (__name__)

''' A graph node '''
class Node:
	def __init__(self, anid, nodeLabel, nodeType):
		self.id = anid
		self.type = nodeType
		self.label = nodeLabel
		self.context = {}
	def getId (self):
		return self.id
	def getType (self):
		return self.type
	def setType (self, type):
		self.type = type
	def getLabel (self):
		return self.label
	def setLabel (self, label):
		self.label = label
	def setContext (self, context):
		self.context = context
	def getContext (self):
		return self.context

''' A gaph edge '''
class Edge:
	def __init__(self, anid, source, target, type):
		self.id = anid
		self.type = type
		self.source = source
		self.target = target
	def getId (self):
		return self.id
	def setType (self, type):
		self.type = type
	def getType (self):
		return self.type
	def setSource (self, source):
		self.source = source
	def getSource (self):
		return self.source
	def setTarget (self, target):
		self.target = target
	def getTarget (self):
		return self.target
	def getLabel (self):
		return self.id

''' A graph '''
class Graph:
	def __init__(self):
		self.nodes = []
		self.edges = []
		self.nodeMap = {}
		self.nodeLabelMap = {}
		self.properties = None
		self.propertyList = []
		self.fileNames = []
	def addFileName (self, fileName):
		if not fileName in self.fileNames:
			self.fileNames.append (fileName)
	def addProperties (self, properties):
		self.propertyList.append (properties)
	def getPropertyList (self):
		return self.propertyList
	def setProperties (self, properties):
		self.properties = properties
	def getProperties (self):
		return self.properties
	def getNodes (self):
		return self.nodes
	def getNode (self, id):
		node = None
		'''
		logger.debug ("getnode: %s %s", id, id in self.nodeMap)
		for i in self.nodeMap:
			logger.debug ("nodemap: id=%s", i)
			'''
		if id in self.nodeMap:
			node = self.nodeMap [id]
		else:
			for n in self.nodes:
				if n.getId () == id:
					logger.debug ("updating nodemap: id=%s", id)
					self.nodeMap [id] = node
					node = n
					break

		return node #self.nodeMap[id] if id in self.nodeMap else None

	def getNodeByLabel (self, label):
		value = None
		if label in self.nodeLabelMap:
			value = self.nodeLabelMap [label]
		return value
	def addNode (self, id, label, type="{}"):

		if "0.0" in label:
			logger.debug ("addnodex")
			traceback.print_stack ()


		node = Node (id, label, type)
		return self.addExistingNode (node)
	def addExistingNode (self, node):
		self.nodes.append (node)
		self.nodeMap [node.getId()] = node
		'''
		logger.debug ("addednode: %s %s gid=%s", node.getId (), node.getLabel (), self)
		for i in self.nodeMap:
			logger.debug ("nodemap: id=%s", i)
			'''
		if not node.getId () in self.nodeMap:
			raise ValueError ("insert failed")
		self.nodeLabelMap[node.getLabel()] = node
		return node
	def removeNode (self, id):
		for node in self.nodes:
			if node.getId () == id:
				self.nodes.remove (node)
		if node.getId () in self.nodeMap:
			del self.nodeMap [node.getId ()]
		if node.getLabel () in self.nodeLabelMap:
			del self.nodeLabelMap [node.getLabel ()]
		logger.debug ("graph remove node: %s %s", id, node.getLabel ())
	def getEdges (self):
		return self.edges
	def addEdge (self, id, source, target, type="{}"):
		edge = Edge (id, source, target, type)
		self.edges.append (edge)
		return edge
	def removeEdge (self, edge):
		self.edges.remove (edge)
	def dump (self):
		for node in self.nodes:
			typeText = None
			type = node.getType ()
			if type:
				typeText = type.replace ("\n", "")
			logger.debug ("--node (%s(%s)(%s)) ", node.getId (), node.getLabel (), typeText)
		for edge in self.edges:
			logger.debug ("edge: src: %s trg: %s", edge.getSource (), edge.getTarget ())
			try:
				source = self.nodeMap [edge.getSource ()]
				target = self.nodeMap [edge.getTarget ()]
				if not source:
					targetText = target.getLabel () if target else " unknown target"
					logger.debug ( "unable to find node for source id %s with target %s", edge.getSource (), targetText)
				elif not target:
					sourceText = source.getLabel () if source else " unknown source"
					logger.debug ("unable to find node for target id %s with source %s", edge.getTarget (), sourceText)
				else:
					logger.debug ("--edge(id=%s)(src=(id=%s):%s, dst=(id=%s):%s), type(%s)",
					       edge.getId(), 
						       source.getId (),
						       source.getLabel (), 
						       target.getId (), 
						       target.getLabel (),
						       edge.getType ())
			except Exception as ex:
				pass

""" GraphML parser """
class GraphMLHandler(xml.sax.handler.ContentHandler):
        def __init__(self, graph=None):
                self.elements = []
		self.idPrefix = 1
		if graph:
			self.graph = graph
			for node in graph.nodes:
				id = node.getId ()
				if id:
					match = re.match ("([0-9]+).*", id)
					if match:
						prefix = int (match.group (1))
						if prefix > self.idPrefix:
							logger.debug ( "setting prefix: %s", prefix)
							self.idPrefix = prefix + 1
		else:
			self.graph = Graph ()
		self.source = None
		self.target = None
		self.type = None
		self.edgeId = None
		self.label = None
		self.nodeId = None
		self.nodeType = None
		self.isDescription = False
	def nextFile (self):
		self.idPrefix += 1
        def startElement (self, element, attrs):
        	self.elements.insert(0, element)
                parent = None
                if len (self.elements) > 1:
                        parent = self.elements[1]
		if element == "graphml":
			x = 0
		elif element == "node":

			self.nodeId = "%s%s" % (self.idPrefix, attrs.get ("id"))
		elif element == "data":
			key = attrs.get ("key")
			if key in ("d5", "d9"):
				self.isDescription = True
				self.nodeType = ""
		elif element == "edge":
			self.edgeId = "%s%s" % (self.idPrefix, attrs.get ("id"))
			self.source = "%s%s" % (self.idPrefix, attrs.get ("source"))
			self.target = "%s%s" % (self.idPrefix, attrs.get ("target"))
        def characters (self, chars):
                parent = self.elements[0]

                if parent == "Label":
			self.label = unicode(chars)
			logger.debug ("graphml-parser: label %s", self.label)
		elif parent == "data":
			if self.isDescription:
				self.nodeType = self.nodeType + unicode(chars)
		elif parent == "y:NodeLabel":
			self.label = unicode(chars)

        def endElement (self, element):
                self.elements = self.elements[1:]
                if element == "node":

			node = self.graph.addNode (self.nodeId, self.label, self.nodeType)
			label = node.getLabel ()
			if label == "properties" or label == "Properties":
				self.graph.addProperties (node)
				logger.debug ("graphml:parse:properties: %s", node.getType ())
			self.nodeId = None
			self.nodeType = None
			self.label = None
		elif element == "edge":
			self.graph.addEdge (self.edgeId, self.source, self.target, self.nodeType)
			self.nodeType = None
			self.source = None
			self.target = None
			self.edgeId = None
		self.isDescription = False			
	def endDocument (self):
		x = 0
		
class GraphMLParser:
	def __init__(self): pass	

	def parseStream (self, stream, url, handler):
		logger.debug ("parser-stream-url: %s" % url)
		xml.sax.parse (stream, handler)
		handler.graph.addFileName (os.path.realpath (url))

	def parseURL (self, url, handler, path=[]):
		stream = None
		HTTP = "http://"
		if not "" in path:
			path.append ("")
		if url.startswith (HTTP):
			stream = urllib2.urlopen (url)
		elif os.path.exists (url):
			stream = open (url)
			self.parseStream (stream, url, handler)
		else:
			parts = url.rsplit (".")
			if len(parts) >= 3: # <package>.<package>.<model>.graphml
				numParts = len (parts)
				packagePath = ""
				for element in parts [ 0 : numParts - 2 ]:
					packagePath = os.path.join (packagePath, element)
				modelName = "%s.%s" % (parts [ numParts - 2 ],
						       parts [ numParts - 1 ])
				url = os.path.join (packagePath, "model", modelName)
			for prefix in path:
				if prefix == "":
					newUrl = url
				else:
					newUrl = "%s/%s" % (prefix, url)
				logger.debug ("parser-detect-url:%s" % newUrl)
				if newUrl.startswith (HTTP):
					stream = urllib2.urlopen (newUrl)
				elif os.path.isfile (newUrl):
					stream = open (newUrl)
				if stream:
					self.parseStream (stream, newUrl, handler)
					break
		if not stream:
			raise ValueError ("unable to find model: %s" % url)
	def parse (self, fname):
		handler = GraphMLHandler ()
		self.parseURL (fname, handle)
		return handler.graph
	def parseMultiple (self, fileNames, path=[], graph=None):
		handler = GraphMLHandler (graph)
		for fileName in fileNames:
			self.parseURL (fileName, handler, path)
			handler.nextFile ()
		return handler.graph
	def parseString (self, string):
		handler = GraphMLHandler ()
		xml.sax.parseString (string, handler)
		return handler.graph
		
__version__ = '0.1'
__all__ = [ "Node", "Edge", "GraphMLParser", "Graph" ]
__author__ = 'Steve Cox <scox@renci.org>'

