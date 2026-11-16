import sys
import kernel0d as zd

######################################################
## Global String Buffer and builtin parsing primitives
######################################################

debugprogress = True
debugtrace = True

def declare (bool):
    return bool

class StringBuffer ():
    def __init__ (self):
        self.buff = ""
        self.bx = 0
        self.marks = []
    def set_input (self, s):
        self.buff = s
    def push_mark (self):
        self.marks.append (self.bx)
    def pop_mark (self):
        self.marks.pop ()
    def rewind (self):
        self.bx = self.marks.pop ()
    def accept_char (self):
        self.bx += 1
    def empty (self):
        return self.bx >= len (self.buff)
    def is_space (self):
        if self.empty ():
            return False
        elif self.buff [self.bx] == " " or self.buff [self.bx] == "," or self.buff [self.bx] == "\n" or self.buff [self.bx] == "\t" :
            return True
    def look (self):
        if self.empty ():
            raise Exception ('look called on empty input buffer')
        else:
            return self.buff [self.bx]
    def buffrepr (self):
        return f"<{self.bx}>{self.buff[self.bx:10].replace('\n', '⤶').replace(' ', '␣').replace('\t', '⇢')}"
    def parse_char (self, c):
        if self.empty ():
            return False
        if c == self.buff [self.bx]:
            self.accept_char ()
            return True
        return False

class Indentation ():
    def __init__ (self):
        self.indent = 0
        self.prefix = ''
    def ind (self):
        self.indent += 1
    def out (self):
        self.indent -= 1
    def pr (self):
        if debugprogress or debugtrace:
            print (" " * self.indent, end="", file=sys.stderr)
            print (self.prefix, end="", file=sys.stderr)
        pass

    
buffer = StringBuffer ()
indent = Indentation ()

def parse_debug_prefix (s):
    global indent
    indent.prefix = s

def pbuffrepr (s):
    global buffer
    print (f'{s}{buffer.buffrepr()}', file=sys.stderr)
    
def fail (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    if debugtrace:
        print (f'fail {s}', file=sys.stderr)
    buffer.rewind ()
    return False

def begin (s):
    global buffer
    global indent
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'begin {s} {buffer.buffrepr()}', file=sys.stderr)
    elif debugtrace:
        print (f'begin {s}', file=sys.stderr)
    buffer.push_mark ()

def accept (s):
    global buffer
    global indent
    indent.out ()
    indent.pr ()
    prev = buffer.pop_mark ()
    if debugprogress or debugtrace:
        print (f'accept {s}', file=sys.stderr)
    return True

def debug (name, s):
    global buffer
    indent.pr ()
    indent.ind ()
    if debugprogress:
        print (f'{name} {s} {buffer.buffrepr()}', file=sys.stderr)
    elif debugtrace:
        print (f'{name} {s}', file=sys.stderr)

def parse_string (s):
    global buffer
    i = 0
    debug ("parse_string", s)
    while i < len (s):
        if buffer.parse_char (s [i]):
            i += 1
            continue
        else:
            return False
    return True

def any ():
    global buffer
    debug ("any", "_")
    if buffer.empty ():
        return False
    else:
        buffer.accept_char ()
        return True
    
def parse_upto (c):
    global buffer
    while True:
        if buffer.empty ():
            return False
        else:
            if c == buffer.look ():
                break
            else:
                buffer.accept_char ()
    return True

def parse_range (first, last):
    global buffer
    if buffer.look () >= first and buffer.look () <= last:
        buffer.accept_char ()
        return True
    else:
        return False

def parse_ignoring (f):
    global buffer
    debug ("ignore", "")
    while (buffer.is_space ()):
        buffer.accept_char ()
    r = f ()
    while (buffer.is_space ()):
        buffer.accept_char ()
    return r

def parse_one_or_more (f):
    parse_debug_prefix ('+')
    if f ():
        while True:
            if f ():
                continue
            else:
                parse_debug_prefix ('')
                return True
    else:
        parse_debug_prefix ('')
        return False
    
def parse_either (flist):
    parse_debug_prefix ('|')
    while True:
        f = flist [0]
        if f ():
            parse_debug_prefix ('')
            return True
        elif flist:
            if len (flist) > 1:
                flist = flist [1:]
            else:
                parse_debug_prefix ('')
                return False
        else:
            parse_debug_prefix ('')
            return False
    raise Exception ("internal error: should not have reached this point")

def parse_set_input (s):
    buffer.set_input (s)





########## PBP Parts #############

### Environment database ###
### a separate stack for each field of the environment
### stkpush (stackvar, "...") push a string onto the stack
### stkpop (stackvar) pop top item (a string) from the stack
### read access via top(stackvar)

### the Envstk is the only writer, all other access is read access

### aside: this seems like explicit dynamic scoping. AFAICT, static scoping devolves into dynamic scoping by using
### the return stack to store parameters, where the code accessing a parameter looks only at the top of the stack where the
### provenance back to earlier history of the variable has been optimized away and is inaccessible (backlinks have been
### optimized away in the effort to save space by not using lists with CDRs). Passing an expression to a parameter creates
### a hidden temp variable

target = []
more = []
logicalop = []
value =[]

def stkpush (stk, val):
    stk.append (val)

def stkpop (stk):
    stk.pop ()

def stktop (stk):
    return stk [-1]


### SeqGroup part - handles chain of Stepper or SeqGroup parts
def SeqGroup_handler (eh, mev):
    global target, more, logicalop, value
    if mev.port == "":
        stkpush (more, "") ; stkpush (logicalop, "and") ; eh.instance_data = "triggered"
        zd.send (eh, "tick", "", mev)
    elif mev.port == "done":
        stkpop (more) ; stkpop (logicalop)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in SeqGroup_handler port={mev.port} payload={mev.payload.v}')

def SeqGroup_reset_handler (eh):
    global target, more, logicalop, value
    if eh.instance_data == "triggered":
        stkpop (more) ; stkpop (logicalop)
        eh.instance_data = None

def SeqGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "SeqGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, SeqGroup_handler, SeqGroup_reset_handler)

def SeqGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("SeqGroup", None, SeqGroup_instantiate))

### AltGroup part - handles chain of Stepper or AltGroup parts
def AltGroup_handler (eh, mev):
    global target, more, logicalop, value
    if mev.port == "":
        stkpush (more, "not") ; stkpush (logicalop, "or") ; eh.instance_data = "triggered"
        zd.send (eh, "tick", "", mev)
    elif mev.port == "done":
        stkpop (more) ; stkpop (logicalop)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in AltGroup_handler port={mev.port} payload={mev.payload.v}')

def AltGroup_reset_handler (eh):
    global target, more, logicalop, value
    if eh.instance_data == "triggered":
        stkpop (more) ; stkpop (logicalop)
        eh.instance_data = None

def AltGroup_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "AltGroup")
    return zd.make_leaf ( name_with_id, owner, None, arg, AltGroup_handler, AltGroup_reset_handler)

def AltGroup_install (reg):
    zd.register_component (reg, zd.mkTemplate ("AltGroup", None, AltGroup_instantiate))


### Stepper - pure control flow - a single step in a sequence of steps
### on "" send a tick to "tick", save myid push new target id
### on "done" send a tick to "", pop myid and target id

def Stepper_handler (eh, mev):
    global myid, targetid, more, logicalop, value
    if mev.port == "":
        zd.send (eh, "tick", "", mev)
    elif mev.port == "done":
        bool = stktop (value)
        if stktop (more) == "not":
            if not bool:
                zd.send (eh, "more", "", mev)
            elif bool:
                zd.send (eh, "skip", "", mev)
        else:
            if bool:
                zd.send (eh, "more", "", mev)
            elif bool:
                zd.send (eh, "skip", "", mev)
    else:
        raise Exception (f"internal error in Stepper_handler port={mev.port} payload={mev.payload.v}")

def Stepper_reset_handler (eh):
    # nothing pushed, nothing to clean up
    pass


def Stepper_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "Stepper")
    return zd.make_leaf ( name_with_id, owner, None, arg, Stepper_handler, Stepper_reset_handler)

def Stepper_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Stepper", None, Stepper_instantiate))


### Initialize Buffer part - starts the parser by storing the string mev.payload.v into the buffer
def InitBuffer_handler (eh, mev):
    if mev.port == "":
        parse_set_input (mev.payload.v)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in InitBuffer_handler port={mev.port} payload={mev.payload.v}')

def InitBuffer_reset_handler (eh):
    pass

def InitBuffer_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "InitBuffer")
    return zd.make_leaf ( name_with_id, owner, None, arg, InitBuffer_handler, InitBuffer_reset_handler)

def InitBuffer_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Initialize Buffer", None, InitBuffer_instantiate))


    
### Parse an "a" from the buffer
def ParseA_handler (eh, mev):
    global myid, targetid, more, logicalop, value
    if mev.port == "":
        bool = parse_string ("a")
        stkpush (value, bool)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in ParseA_handler port={mev.port} payload={mev.payload.v}')

def ParseA_reset_handler (eh):
    pass

def ParseA_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "ParseA")
    return zd.make_leaf ( name_with_id, owner, None, arg, ParseA_handler, ParseA_reset_handler)

def ParseA_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Parse A", None, ParseA_instantiate))

### Parse an "a" from the buffer
def ParseB_handler (eh, mev):
    global myid, targetid, more, logicalop, value
    if mev.port == "":
        bool = parse_string ("b")
        stkpush (value, bool)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in ParseB_handler port={mev.port} payload={mev.payload.v}')

def ParseB_reset_handler (eh):
    pass

def ParseB_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "ParseB")
    return zd.make_leaf ( name_with_id, owner, None, arg, ParseB_handler, ParseB_reset_handler)

def ParseB_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Parse B", None, ParseB_instantiate))

### Parse an "a" from the buffer
def ParseB_handler (eh, mev):
    global myid, targetid, more, logicalop, value
    if mev.port == "":
        bool = parse_string ("b")
        stkpush (value, bool)
        zd.send (eh, "", "", mev)
    else:
        raise Exception (f'internal error in ParseB_handler port={mev.port} payload={mev.payload.v}')

def ParseB_reset_handler (eh):
    pass

def ParseB_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "ParseB")
    return zd.make_leaf ( name_with_id, owner, None, arg, ParseB_handler, ParseB_reset_handler)

def ParseB_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Parse B", None, ParseB_instantiate))



### Finalize by popping the value stack and sending the value as a string
def PopValue_handler (eh, mev):
    global myid, targetid, more, logicalop, value
    if mev.port == "":
        bool = stktop (value)
        stkpop (value)
        zd.send (eh, "", str (bool), mev)
    else:
        raise Exception (f'internal error in PopValue_handler port={mev.port} payload={mev.payload.v}')

def PopValue_reset_handler (eh):
    pass

def PopValue_instantiate (reg,owner,name, arg, template_data):
    name_with_id = zd.gensymbol ( "PopValue")
    return zd.make_leaf ( name_with_id, owner, None, arg, PopValue_handler, PopValue_reset_handler)

def PopValue_install (reg):
    zd.register_component (reg, zd.mkTemplate ("Pop Value", None, PopValue_instantiate))
    
    
    
