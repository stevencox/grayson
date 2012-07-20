# -*- coding: utf-8 -*-

''' system '''
from string import Template
import json
import logging
import string
import traceback

logger = logging.getLogger (__name__)

class ASTProfile (object):
    def __init__(self, namespace, key, value):
        self.namespace = namespace
        self.key = key
        self.value = value
    
''' Abstract representation of an element comprising '''
class ASTElement:

    def __init__(self, node):
        self.ATTR_TYPE = "type"
        self.node = node
        self.properties = { "id" : self.node.getId () }
        self.daxNode = None
        properties = self.parseProperties ()
        if properties:
            self.setProperties (properties)
            
    def parseProperties (self):
        properties = None
        id = self.node.getId ()
        text = self.node.getType ()
        if id and text:
            try:
                text = string.replace (text, "\n", " ")
                properties = json.loads (text)
                logger.debug ("properties %s", properties)
            except:
                message = "ERROR:ast:parse-json: node(id=%s, label=%s, json=%s)" % (id, self.node.getLabel (), text)
                logger.error (message)
                self.setProperties ({ "type" : None })
                traceback.print_exc ()
                raise ValueError (message)
        return properties

    def getProperties (self):
        return self.properties

    def setProperties (self, properties):
        logger.debug ("ast:setprop: (%s,%s)=>%s", self.getId(), self.getLabel (), properties)
        if not properties:
            properties = {}
        self.properties = properties
        self.properties ["id"] = self.node.getId ()
            
    def addAncestor (self, ancestor):
        if ancestor:
            self.mergePropertiesFrom (ancestor)
            
    def addProfiles (self, other):
        if other:
            self.mergePropertiesFrom (other, tag="inherit-profiles")

    def mergePropertiesFrom (self, other, exceptions=["id", "type"], tag="inherit"):
        if other:
            self.properties = self.mergePropertiesDeep (self.properties,
                                                        other.getProperties (),
                                                        exceptions)
            logger.debug ("ast:%s: obj(%s)<-anc(%s)=[%s]" % 
                          (tag,
                           self.node.getLabel(),
                           other.getNode().getLabel (),
                           self.properties))
            
    def mergePropertiesDeep (self, left, right, exceptions=[]):
        if left and right:
            for key in right:
                if key in exceptions:
                    continue
                value = right [key]
                if key in left:
                    if type(value) == dict:
                        value = self.mergePropertiesDeep (left[key], value)
                    else:
                        logger.debug ("ast:keep-key: left[%s]->[%s]" % (key, value))
                else:
                    left [key] = right [key]
                    logger.debug ("ast:copy-key: left[%s]->[%s]" % (key, value))
        return left

    def get (self, key):
        value = None
        if key in self.properties:
            value = self.properties [key]
        return value

    def set (self, key, value):
        self.properties [key] = value
	
    def getLabel (self):
        return self.node.getLabel ()

    def getId (self):
        return self.node.getId ()

    def getType (self):
        return self.get(self.ATTR_TYPE)
    
    def getNode (self):
        return self.node

    def getContext (self):
        return self.node.getContext ()

    def setDaxNode (self, daxNode):
        self.daxNode = daxNode

    def getDaxNode (self):
        return self.daxNode
    
    def getProfiles (self):
        profiles = None
        if self.properties:
            profileList = None
            if 'profiles' in self.properties:
                profileList = self.properties ['profiles']
                if profileList:
                    profiles = []
                    for namespace in profileList:
                        space = profileList [namespace]
                        for key in space:
                            if key:
                                value = space [key]
                                if value:
                                    logger.debug ("ast:get-profiles: (%s)-(%s=%s)" % (namespace, key, value))
                                    profile = ASTProfile (namespace, key, value)
                                    profiles.append (profile)
        return profiles

    def setProfile (self, key, value):
        if not 'profiles' in self.properties:
            self.properties ['profiles'] = {}
        profiles = self.properties ['profiles']
        profiles [key] = value

    def getOrigins (self, graph):
        origins = []
        if self.node:
            edges = graph.getEdges ()
            id = self.node.getId ()
            for edge in edges:
                # this edge points at this node #
                if edge.getTarget () == id:
                    origin = graph.getNode (edge.getSource ())
                    # record the originating node #
                    if origin:
                        logger.debug ("ast:add-origin: ((%s)%s) of ((%s)%s)" % (origin.getId(),
                                                                                     origin.getLabel(), 
                                                                                     self.getId(),
                                                                                     self.getLabel()) )
                        origins.append (origin.getId ())
        return origins

    def getSourceEdges (self, graph, edgeType=None):
        originEdges = []
        if self.node:
            edges = graph.getEdges ()
            id = self.node.getId ()
            for edge in edges:
                # this edge points at this node #
                if edge.getTarget () == id:
                    originEdges.append (edge)
        return originEdges

    def getAncestorsByType (self, graph, type, ancestors = []):
        if self.node:
            edges = graph.getEdges ()
            id = self.node.getId ()
            for edge in edges:
                # this edge points at this node #
                if edge.getTarget () == id:
                    ancestor = graph.getNode (edge.getSource ())
                    # record the originating node #
                    if ancestor:
                        logger.debug ("ast:add-ancestor: (%s) of (%s)" % (ancestor.getLabel(), self.getLabel()) )
                        if ancestor.getId () in ancestors:
                            raise ValueError ("invalid use of getAncestorsByType on a graph with cycles.")
                        ancestors.append (ancestor.getId ())
                        self.getAncestorsByType (graph, type, ancestors)
        return ancestors

    def getTargets (self, graph):
        targets = []
        if self.node:
            edges = graph.getEdges ()
            id = self.node.getId ()
            for edge in edges:
                # this edge points at this node #
                if edge.getSource () == id:
                    target = graph.getNode (edge.getTarget())
                    # record the originating node #
                    if target:
                        logger.debug ("ast:add-target: (%s) of (%s)" % (target.getLabel(), self.getLabel()) )
                        targets.append (target.getId ())
                    else:
                        nodes = graph.getNodes ()
                        for node in nodes:
                            logger.debug ("    --> label(%s) \t id=(%s)", node.getLabel (), node.getId ())

                        logger.debug ("___________ FAIL couldn't get target %s for node %s %s", edge.getTarget (), self.getLabel (), graph)
        return targets

    def getTargetEdges (self, graph):
        targetEdges = []
        if self.node:
            edges = graph.getEdges ()
            id = self.node.getId ()
            for edge in edges:
                # this edge points at this node #
                if edge.getSource () == id:
                    targetEdges.append (edge)
        return targetEdges
            
if __name__ == '__main__':
    test_grayson_compiler ()



