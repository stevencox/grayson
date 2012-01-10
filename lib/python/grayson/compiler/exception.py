
class GraysonCompilerException (Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return self.value

class CycleException (GraysonCompilerException):
     def __init__(self, value):
          self.value = value
     def __str__(self):
          return self.value

class SyntaxError (GraysonCompilerException):
     def __init__(self, value):
          self.value = value
     def __str__(self):
          return self.value

class CompositeError (GraysonCompilerException):
     def __init__(self, values):
          self.values = values
     def __str__(self):
          buffer = []
          for val in self.values:
               buffer.append (val.__str__ ())
          return '\n'.join (buffer)
