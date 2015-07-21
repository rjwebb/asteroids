
#  Copyright (C) 2006, 2007, 2008 Peter Robinson
#  Email: pjr@itee.uq.edu.au
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

""" Pedro client module.

This module defines the client interface for Pedro.

The main components are:

PObject and subclasses -- Prolog terms

PedroParser class and support -- parsing strings representing Prolog terms
into Prolog Objects

PedroClient class -- The Pedro client interface class

"""

import re, socket, threading, Queue, select


# Classes for Prolog terms

class PObject(object):

    """ The Prolog object base class.
    This is intended as an abstract class.
    
    """
    
    # type tags
    inttype = 0
    floattype = 1
    vartype = 2
    stringtype = 3
    atomtype = 4
    listtype = 5
    structtype = 6

    # to keep pychecker happy
    def __init__(self):
        self.type = PObject.inttype
        self.val = 0
    
    def __str__(self):
        return str(self.val)
    
    def get_type(self):
        return self.type


class PInteger(PObject):
            
    """ Prolog integer subclass of PObject. """
    
    def __init__(self, v):
        """ v is the integer value of this object."""
        self.val = v
        self.type = PObject.inttype


class PFloat(PObject):
                
    """ Prolog float subclass of PObject. """
    
    def __init__(self, v):
        """ v is the float value of this object."""
        self.val = v
        self.type = PObject.floattype


class PVar(PObject):
                
    """ Prolog variable subclass of PObject. """
        
    def __init__(self,name):
        """ name is the name of this object."""
        self.val = name
        self.type = PObject.vartype


class PString(PObject):                

    """ Prolog string subclass of PObject. """      

    def __init__(self,chars,unescape = False):
        """ chars is the string value of this object."""
        if unescape:
            stripped_chars = chars[1:-1] # strip off the quotes
            self.val = stripped_chars.decode('string-escape') # un-escape the string
        else:
            self.val = chars
        self.type = PObject.stringtype

    def __str__(self):
        """ return the string representation - escape + escape " + add quotes. """
        escaped_chars = self.val.encode('string-escape')
        return '"'+self.val.replace('"', '\\\\"')+'"'
    

class PAtom(PObject):

    """ Prolog atom subclass of PObject. """        

    @classmethod
    def atomize(cls, stringOrAtom):
        if stringOrAtom.__class__ == PAtom:
            return stringOrAtom
        else:
            return PAtom(stringOrAtom)
 
    def __init__(self,name):
        """ name is the name of this object."""
        self.val = name
        self.type = PObject.atomtype


class PList(PObject):

    """ Prolog list subclass of PObject.

    Stored as a cons pair.

    """
    
    def __init__(self,h,t):
        """  h and t are the head an tail of the list."""
        self.head = h
        self.tail = t
        self.type = PObject.listtype

    def __str__(self):
        """ Display the Prolog list in standard Prolog form. """
        
        head = self.head
        tail = self.tail
        s = '[' + str(head)
        while tail.type == PObject.listtype:
            head = tail.head
            tail = tail.tail
            s += ', ' + str(head)
        if tail.val == '[]':
            s += ']'
        else:
            s += '|'+str(tail)+']'
        return s
            
    def toList(self):
        """ Return a Python list from the Prolog list

        return None if list does not end with a []
        """

        lst = []
        head = self.head
        lst.append(head)
        tail = self.tail
        while tail.type == PObject.listtype:
            head = tail.head
            lst.append(head)
            tail = tail.tail
        if tail.val == '[]':
            return lst
        else:
            return None

class PStruct(PObject):

    """ Prolog structure subclass of PObject.

    Stored as the functor and a Python list of Prolog terms representing
    the arguments of the strudture.
    
    """
    def __init__(self,f,lst):
        """ f is the functor term and lst is the argument list. """
        self.functor = PAtom.atomize(f)
        self.args = lst
        self.type = PObject.structtype

    def arity(self):
        """ Return the arity of the structure. """
        return len(self.args)
    
    def __str__(self):
        """ Display the Prolog structure in standard Prolog form. """
        s = str(self.functor) + '(' + str(self.args[0])
        for i in self.args[1:]:
            s = s + ', ' + str(i)
        s = s + ')'
        return s


class ParseError(Exception):
    
    """ An exception object for parsing."""
    
    def __init__(self, pos):
        self.pos = pos

    def __str__(self):
        return repr(self.pos)


# A regular expression to distinguish between strings representing
# integers and floats
_floatRE = re.compile("[.eE]")

def _number_convert(x):
    """ Return the tagged token of the input string representing a number."""
    if (_floatRE.search(x)):
        return ('float', float(x))
    else:
        return ('int', int(x))

# A table of regular expressions that recognise tokens of various types
# and functions for conveting such strings into tagged tokens
_retable = (
    (  # for number tokens
    re.compile(r"""
    \d+
    (?:\.\d+)?(?:[eE][+-]?\d+)?
    """, re.VERBOSE),
    _number_convert
    ),
    (  # for the tokens ( ) [ ] ,
    re.compile(r"""
    \( | \) | \[ | \] | , | \|
    """, re.VERBOSE),
    lambda x: ('sym', x)
    ),
    (  # for variable tokens
    re.compile(r"""
    [A-Z][A-Za-z0-9_]*
    """, re.VERBOSE),
    lambda x: ('var', x)
    ),
    (  # for string tokens
    re.compile(r"""
    \"[^\"\\]*(?:\\.[^\"\\]*)*\"
    """, re.VERBOSE),
    lambda x: ('string', x)
    ),
    (  # for atom tokens
    re.compile(r"""
    [a-z][A-Za-z0-9_]* |
    '[^'\\]*(?:\\.[^'\\]*)*' |
    [-/+*<=>#@$\\^&~`:.?!;]+ |
    {}
    """, re.VERBOSE),
    lambda x: ('atom', x)
    ),
    (  # catchall
    re.compile(r"""
    .*
    """, re.VERBOSE),
    lambda x: ('eos', 'eos')
    )
)

# A regular expression used for consuming spaces in the parser
_spacesRE = re.compile('\s*')

class PedroParser:
    
    """A parser for Prolog terms used in Pedro.

    The method parse(string) returns a Prolog term (using Prolog term
    classes). An exception is thrown if the string does not parse.

    """
    def __init__(self):
        """ Set the string to be pased and the position in the string."""

        self.string = ''
        self.pos = 0

    def __next_token(self):
        """ Return the next tagged token from string at position pos. """

        self.pos = _spacesRE.match(self.string, self.pos).end()
        for (regexp, fun) in _retable:
            m = regexp.match(self.string, self.pos)
            if m:
                self.curr_token = fun(m.group())
                self.pos = m.end()
                break

    # return the list of terms representing structure argument
    def __parseargs(self):
        """ Return the list of prolog terms of an argument list."""

        t1 = [self.__prec700()]
        while (self.curr_token[1] == ','):
            self.__next_token()
            t2 = self.__prec700()
            t1.append(t2)
        return t1

    # return the list of terms representing list elements
    def __parselistargs(self):
        """ Return the list of prolog terms from a list."""
        t1 = self.__prec700()
        if (self.curr_token[1] == ','):
            self.__next_token()
            t2 = self.__parselistargs()
            return PList(t1, t2)
        elif self.curr_token[1] == '|':
            self.__next_token()
            t2 = self.__prec700()
            return PList(t1, t2)
        else:
            return PList(t1, PAtom('[]'))

    # parsing a basic term
    def __basic(self):
        """ Return a simple parsed term."""
        # nothing left - error
        if (self.curr_token[0] == 'eos'):
            raise ParseError, self.pos
        # a string token 
        if (self.curr_token[0] == 'string'):
            t1 = PString(self.curr_token[1], True)
            self.__next_token()
            return t1
        # a var token
        if (self.curr_token[0] == 'var'):
            t1 = PVar(self.curr_token[1])
            self.__next_token()
            return t1
        # an int token
        if (self.curr_token[0] == 'int'):
            t1 = PInteger(self.curr_token[1])
            self.__next_token()
            return t1
        # a float token
        if (self.curr_token[0] == 'float'):
            t1 = PFloat(self.curr_token[1])
            self.__next_token()
            return t1
        # the start of a bracketed term
        # error if not terminated by a closing bracket
        if (self.curr_token[1] == '('):
            self.__next_token()
            t1 = self.__prec1100()
            if (self.curr_token[1] == ')'):
                self.__next_token()
                return t1
            raise ParseError,self.pos
        # the start of a Prolog list
        # error if not terminated by ]
        if (self.curr_token[1] == '['):
            self.__next_token()
            if (self.curr_token[1] == ']'):
                self.__next_token()
                return PAtom('[]')
            t1 = self.__parselistargs()
            if (self.curr_token[1] == ']'):
                self.__next_token()
                return t1
            raise ParseError, self.pos
        # at this point the current token is an atom token
        t1 = PAtom(self.curr_token[1])
        self.__next_token()
        if (self.curr_token[1] != '('):
            return t1
        # we have a structured term - e.g. f(a1, a2)
        self.__next_token()
        t2 = self.__parseargs()
        if (self.curr_token[1] == ')'):
            self.__next_token()
            t2 = PStruct(t1, t2)
            return t2
        raise ParseError, self.pos

    def __prec50(self):
        """ Parse a precedence 50 term. """
        
        t1 = self.__basic()
        if (self.curr_token[1] == ':'):
            op = PAtom(':')
            self.__next_token()
            t2 = self.__basic()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec100(self):
        """ Parse a precedence 100 term. """
            
        t1 = self.__prec50()
        if (self.curr_token[1] == '@'):
            op = PAtom('@')
            self.__next_token()
            t2 = self.__prec50()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec200(self):
        """ Parse a precedence 200 term. """
            
        if (self.curr_token[0] == 'eos'):
            raise ParseError, self.pos
        if (self.curr_token[1] == '-'):
            self.__next_token()
            t2 = self.__prec100()
            # if we have - as a prefix operator followed by a number
            # then return the negated number
            if (t2.get_type() == PObject.inttype) or \
               (t2.get_type() == PObject.floattype):
                t2.val *= -1
                return t2
            op = PAtom('-')
            return PStruct(op, [t2])
        t1 = self.__prec100()
        if (self.curr_token[1] == '**'):
            op = PAtom('**')
            self.__next_token()
            t2 = self.__prec100()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec400(self):
        """ Parse a precedence 400 term with left associative ops."""

        t1 = self.__prec200()   
        while (self.curr_token[1] in
            ('*', '/', '//', 'mod', '>>', '<<')):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec200()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec500(self):
        """ Parse a precedence 500 term with left associative ops."""

        t1 = self.__prec400()   
        while (self.curr_token[1] in ('+','-', '\\/', '/\\')):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec400()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec700(self):
        """ Parse a precedence 700 term."""

        t1 = self.__prec500()
        if (self.curr_token[1] in ('=', 'is', '<', '>', '=<', '>=')):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec500()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec1000(self):
        """ Parse a precedence 1000 term."""

        t1 = self.__prec700()
        if (self.curr_token[1] == ','):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec1000()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec1050(self):
        """ Parse a precedence 1050 term."""

        t1 = self.__prec1000()
        if (self.curr_token[1] == '->'):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec1050()
            t1 = PStruct(op, [t1, t2])
        return t1

    def __prec1100(self):
        """ Parse a precedence 1100 term."""

        t1 = self.__prec1050()
        if (self.curr_token[1] == ';'):
            op = PAtom(self.curr_token[1])
            self.__next_token()
            t2 = self.__prec1100()
            t1 = PStruct(op, [t1, t2])
        return t1

    def parse(self, str):
        """ Parse str into a Prolog term.

        An error is thrown if the string does not parse.

        """
        
        self.string = str
        self.pos = 0
        self.__next_token()
        # try:
        t = self.__prec1100()
        if (self.curr_token[0] != 'eos'):
            raise ParseError, self.pos
        return t
#except ParseError, e:
#    print "Parse error at position", e.pos
#    return None



running = True

class Reader( threading.Thread ):
    """The message reader thread."""

    def __init__( self, q, sock ):
        self.q = q
        self.sock = sock
        threading.Thread.__init__(self)

    def run( self ):
        buff = ""
        while (running):
            chars = self.sock.recv(1024)
            if (chars == ''):
                break
            buff = buff + chars
            pos = buff.find('\n')
            while (pos != -1):
                message = buff[:pos]
                self.q.put(message)

                buff = buff[(pos+1):]
                pos = buff.find('\n')

# for testing if a P2P address is a variable
_p2p_var_addr = re.compile("^[_A-Z][^:]*$")

class PedroClient:
    """ A Pedro Client.

    The client is connected to the server on initialization.
    The methods are:
    disconnect() - disconnect from server
    
    connect() - reconnect to server
    
    notify(term) - send a notification to the server - term is
    a string representation of a Prolog term - 1 is returned if
    the server accepts term; 0 otherwise.

    subscribe(term, goal) - subscribe to terms that match term and
    that satisfy goal. Both term and goal are string representations
    of Prolog terms. The ID of the subscription is returned. The ID is
    0 if the subscription failed.

    unsubscribe(id) - unsubscribe to a previous subscription with ID id
    - ID is returned if the server succeeds in unsubscribing; otherwise
    0 is returned.

    register(myname) - register myname as my name with the server - 0 is
    returned iff registration failed.

    deregister() - deregister with server.

    p2p(addr, term) - send term as a p2p message to addr.

    get_notification() - get the first notification from the message queue
    of notifications sent from the server as a string.

    get_term() - the same as get_notification except the message is parsed
    into a representation of a Prolog term - see PedroParser.

    notification_ready() - test if a notification is ready to read.

    parse_string(string) - parse string into a Prolog term.
    """
    
    def __init__(self, machine='localhost', port=4550, async = True):
        """ Initialize the client.

        machine -- then address of the machine the Pedro server is running.
        port -- the port the Pedro server is using for connections.
        async -- determines if messages are read asynchronously
        
        """
        self.machine = machine
        self.port = port
        self.connected = False
  	self.async = async
        self.connect()
        self.name = ''
        
    def getDataSocket(self):
        """ Get the Data Socket """

        return self.datasock

    def connect(self):
        """ Make the connection to Pedro. """
        
        if (self.connected):
            return 0
        else:
            running = True
            # connect to info
            infosock = socket.socket()
            infosock.connect((self.machine, self.port))
            # get info from server on info socket
            pos = -1
            buff = ''
            while (pos == -1):
                chars = infosock.recv(64)
                buff = buff + chars
                pos = buff.find('\n')
            parts = buff.split()
            self.machine = parts[0]
            ack_port = int(parts[1])
            data_port = int(parts[2])
            infosock.close()
            # connect to ack
            self.acksock = socket.socket()
            self.acksock.connect((self.machine, ack_port))
            # get my ID
            pos = -1
            buff = ''
            while (pos == -1):
                chars = self.acksock.recv(32)
                buff = buff + chars
                pos = buff.find('\n')
            self.id_string = buff
            # connect to data
            self.datasock = socket.socket()
            self.datasock.connect((self.machine, data_port))
            self.datasock.send(self.id_string)
            # get ok from server on data socket
            pos = -1
            buff = ''
            while (pos == -1):
                chars = self.datasock.recv(32)
                buff = buff + chars
                pos = buff.find('\n')
            if buff != 'ok\n':
                try:
                    self.acksock.shutdown(socket.SHUT_RDWR)
                    self.acksock.close()
                    self.datasock.shutdown(socket.SHUT_RDWR)
                    self.datasock.close()
                except:
                    pass
                return 0
            ip = self.acksock.getsockname()[0]
            try:
                # if DNS lookup works then the following will succeed
                self.my_machine_name = socket.gethostbyaddr(ip)[0]
                socket.getaddrinfo(self.my_machine_name, 0)
                # check that we get the same IP back OW use original IP
                if ip != socket.gethostbyname(self.my_machine_name):
                    self.my_machine_name = ip
            except:
                # otherwise set to ip
                self.my_machine_name = ip

            self.q = Queue.Queue(0)
            self.parser = PedroParser()
            self.connected = True
            if self.async:
                thread = Reader(self.q, self.datasock)
                thread.setDaemon(True)
                thread.start()
            else:
                self.buff = ''
            return 1

    def disconnect(self):
        """ Disconnect the client. """
        
        if (self.connected):
            running = False
            self.connected = False
            try:
                self.acksock.shutdown(socket.SHUT_RDWR)
                self.acksock.close()
                self.datasock.shutdown(socket.SHUT_RDWR)
                self.datasock.close()
            except:
                pass
            return 1
        else:
            return 0
                    
    def get_ack(self):
        """ Get an acknowledgement from the server. """
        
        pos = -1
        buff = ''
        while (pos == -1):
            chars = self.acksock.recv(32)
            buff = buff + chars
            pos = buff.find('\n')
        r = int(buff)   
        return r
    
    def notify(self, term):
        """ Send a notification to the server and return the ack. """
        
        if (self.connected):
            self.datasock.send(str(term)+'\n')
            return self.get_ack()
        else:
            return 0
            
    def subscribe(self, term, goal = "true", rock = 0):
        """ Send a subscription to the server and return the ack. """
        
        if (self.connected):
            self.datasock.send('subscribe(' + str(term) + ', (' +
                           str(goal) + '), ' + str(rock) + ')\n')
            return self.get_ack()
        else:
            return 0


    def unsubscribe(self, id):
        """ Send an unsubscription to the server and return the ack. """
        
        if (self.connected):
            self.datasock.send('unsubscribe(' + str(id) + ')\n')
            return self.get_ack()
        else:
            return 0


    def register(self, name):
        """ Register the client's name with the server and return the ack. """
        
        if (self.connected):
            self.datasock.send('register(' + name + ')\n')
            ack = self.get_ack()
            if (ack != 0):
                    self.name = name 
            return ack
        else:
            return 0

    def deregister(self):
        """ Unregister the client's name with the server and return the ack. """
        
        if (self.connected):
            self.datasock.send('deregister(' + self.name + ')\n')
            ack = self.get_ack()
            if (ack != 0):
                self.name = ''
            return ack
        else:
            return 0

    def addr2str(self, addr):
        if isinstance(addr, str):
            return addr
        assert isinstance(addr, PStruct)
        assert addr.functor.val == '@' and addr.arity() == 2
        host = addr.args[1]
        name = addr.args[0]
        if isinstance(name, PStruct):
            assert name.functor.val == ':' and name.arity() == 2
            return str(name.args[0]) + ':'+ str(name.args[1]) + '@' + str(host)
        else:
            return str(name) + '@' + str(host)

    def p2p(self, toaddr, term):
        """ Send a p2p message to the server and return the ack. """
        #print toaddr
        straddr = self.addr2str(toaddr)
        name = self.my_machine_name
        if (self.name == ''):
            return 0
        elif '@' in straddr:
            straddr = straddr.replace('localhost', "'"+name+"'")
            self.datasock.send('p2pmsg(' + straddr + ', '\
                               + self.name + "@'" + name\
                               +  "'," + str(term) + ')\n')
            return self.get_ack()
        elif _p2p_var_addr.match(toaddr):
            self.datasock.send('p2pmsg(' + straddr \
                                   + ", " \
                                   + self.name + "@'" + name\
                                   +  "'," + str(term) + ')\n')
            return self.get_ack()
        else:
            self.datasock.send('p2pmsg(' + straddr \
                                   + "@'" + name + "', " \
                                   + self.name + "@'" + name\
                                   +  "'," + str(term) + ')\n')
            return self.get_ack()

    def _pop_rock(self, str):
        """Gets the rock off of the message, returning (message_to_parse, rock)"""
        rock, message = str.split(" ", 1)
        return (message, int(rock))

    def get_notification(self):
        """ Return the next notification and rock received. """
        if self.async or not self.q.empty():
            buf = self.q.get()
            return self._pop_rock(buf)
        else:
            return None

    def get_term(self):
        """ Return the next notification received as a Prolog term together with the rock.

        """

        if self.async or not self.q.empty():
            buf = self.q.get()
            msg, rock = self._pop_rock(buf)
            return (self.parser.parse(msg), rock)
        else:
            return None

    def parse_string(self, string):
        """Return string as a Prolog term"""
        return self.parser.parse(string)

    def notification_ready(self):
        """ Return True iff a notification is ready to read. """
        if not self.async:
            # if sync then read any messages here
            # otherwise the read thread does the work
            sin,_,_ = select.select([self.datasock], [], [], 0)
            while sin:
                chars = self.datasock.recv(1024)
                if (chars == ''):
                    break
                self.buff = self.buff + chars
                pos = self.buff.find('\n')
                while (pos != -1):
                    s = self.buff[:pos]
                    self.buff = self.buff[(pos+1):]
                    pos = self.buff.find('\n')
                    self.q.put(s)
                sin,_,_ = select.select([self.datasock], [], [], 0)
        return not self.q.empty()

